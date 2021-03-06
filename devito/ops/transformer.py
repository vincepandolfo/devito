import cgen
import numpy as np

from collections import defaultdict

from devito import Eq
from devito.ir.equations import ClusterizedEq
from devito.ir.iet import (Call, Callable, Element, Expression, FindNodes, FindSymbols,
                           IterationTree, List)
from devito.ops.node_factory import OPSNodeFactory
from devito.ops.types import OPSBlock, OPSDat, FunctionTimeAccess, ArrayAccess
from devito.ops.utils import (extend_accesses, generate_ops_stencils, get_accesses,
                              namespace)
from devito.tools import dtype_to_cstr
from devito.types import Constant, Indexed
from devito.types.basic import FunctionPointer, Symbol, SymbolicArray, String
from devito.symbolics.extended_sympy import Macro, Byref, ListInitializer

OPS_WRITE = FunctionPointer("OPS_WRITE")
OPS_READ = FunctionPointer("OPS_READ")


def opsit(trees, count):
    node_factory = OPSNodeFactory()
    expressions = []
    for tree in trees:
        expressions.extend(FindNodes(Expression).visit(tree.inner))

    it_range = []
    it_dims = 0
    for tree in trees:
        if isinstance(tree, IterationTree):
            it_range = [it.bounds() for it in tree]
            it_dims = len(tree)

    block = OPSBlock(namespace['ops_block'](count))
    block_init = Element(cgen.Initializer(
        block,
        Call("ops_decl_block", [it_dims, String(block.name)], False)
    ))

    ops_expressions = []
    accesses = defaultdict(set)

    for i in reversed(expressions):
        extend_accesses(accesses, get_accesses(i.expr))
        ops_expressions.insert(0, Expression(make_ops_ast(i.expr, node_factory)))

    ops_stencils_initializers, ops_stencils = generate_ops_stencils(accesses)

    to_remove = [f.name for f in FindSymbols('defines').visit(List(body=expressions))]

    parameters = FindSymbols('symbolics').visit(List(body=ops_expressions))
    parameters = [
        p for p in parameters
        if p.name != 'OPS_ACC_size' and p.name not in to_remove
    ]
    parameters = sorted(parameters, key=lambda i: (i.is_Constant, i.name))

    arguments = FindSymbols('symbolics').visit(List(body=expressions))
    arguments = [a for a in arguments if a.name not in to_remove]
    arguments = sorted(arguments, key=lambda i: (i.is_Constant, i.name))

    ops_expressions = [
        Expression(
            fix_ops_acc(e.expr, [p.name for p in parameters])
        ) for e in ops_expressions
    ]

    callable_kernel = Callable(
        namespace['ops_kernel'](count),
        ops_expressions,
        "void",
        parameters
    )

    dat_declarations = []
    argname_to_dat = {}

    for a in arguments:
        if a.is_Constant:
            continue

        dat_dec, dat_sym = to_ops_dat(a, block)
        dat_declarations.extend(dat_dec)

        argname_to_dat.update(dat_sym)

    par_loop_range_arr = SymbolicArray(
        name=namespace['ops_range'](count),
        dimensions=(len(it_range) * 2,),
        dtype=np.int32
    )
    range_vals = []
    for mn, mx in it_range:
        range_vals.append(mn)
        range_vals.append(mx)
    par_loop_range_init = Expression(ClusterizedEq(Eq(
        par_loop_range_arr,
        ListInitializer(range_vals)
    )))

    ops_args = get_ops_args(
        [p for p in parameters], ops_stencils, argname_to_dat
    )

    par_loop = Call("ops_par_loop", [
        FunctionPointer(callable_kernel.name),
        String(callable_kernel.name),
        block,
        it_dims,
        par_loop_range_arr,
        *ops_args
    ])

    return (
        callable_kernel,
        [par_loop_range_init, block_init] +
        ops_stencils_initializers + dat_declarations +
        [Call("ops_partition", [String("")])],
        List(body=[par_loop]),
        it_dims
    )


def get_ops_args(args, stencils, name_to_dat):
    ops_args = []

    for arg in args:
        if arg.is_Constant:
            ops_args.append(
                Call(
                    "ops_arg_gbl",
                    [
                        Byref(Constant(name=arg.name[1:])),
                        1,
                        String(dtype_to_cstr(arg.dtype)),
                        OPS_READ
                    ], False
                )
            )
        else:
            ops_args.append(
                Call(
                    "ops_arg_dat",
                    [
                        name_to_dat[arg.name],
                        1,
                        stencils[arg.name],
                        String(dtype_to_cstr(arg.dtype)),
                        OPS_WRITE if arg.is_Write else OPS_READ
                    ], False)
            )

    return ops_args


def to_ops_dat(function, block):
    ndim = function.ndim - (1 if function.is_TimeFunction else 0)
    dim = SymbolicArray(
        name="%s_dim" % function.name,
        dimensions=(ndim,),
        dtype=np.int32
    )

    base = SymbolicArray(
        name="%s_base" % function.name,
        dimensions=(ndim,),
        dtype=np.int32
    )

    d_p = SymbolicArray(
        name="%s_d_p" % function.name,
        dimensions=(ndim,),
        dtype=np.int32
    )

    d_m = SymbolicArray(
        name="%s_d_m" % function.name,
        dimensions=(ndim,),
        dtype=np.int32
    )

    res = []
    dats = {}
    ops_decl_dat_call = []

    if function.is_TimeFunction:
        time_pos = function._time_position
        time_index = function.indices[time_pos]
        time_dims = function.shape[time_pos]

        dim_shape = function.shape[:time_pos] + function.shape[time_pos + 1:]
        padding = function.padding[:time_pos] + function.padding[time_pos + 1:]
        halo = function.halo[:time_pos] + function.halo[time_pos + 1:]
        base_val = [0 for i in range(ndim)]
        d_p_val = tuple([p[0] + h[0] for p, h in zip(padding, halo)])
        d_m_val = tuple([-(p[1] + h[1]) for p, h in zip(padding, halo)])

        ops_dat_array = SymbolicArray(
            name="%s_dat" % function.name,
            dimensions=[time_dims],
            dtype="ops_dat",
        )

        ops_decl_dat_call.append(Element(cgen.Statement(
            "%s %s[%s]" % (
                ops_dat_array.dtype,
                ops_dat_array.name,
                time_dims
            )
        )))

        for i in range(time_dims):
            access = FunctionTimeAccess(function, i)
            ops_dat_access = ArrayAccess(ops_dat_array, i)
            call = Call(
                "ops_decl_dat",
                [
                    block,
                    1,
                    dim,
                    base,
                    d_m,
                    d_p,
                    access,
                    String(function._C_typedata),
                    String("%s%s%s" % (function.name, time_index, i))
                ],
                False
            )
            dats["%s%s%s" % (function.name, time_index, i)] = ArrayAccess(
                ops_dat_array,
                Symbol("%s%s" % (time_index, i))
            )
            ops_decl_dat_call.append(
                Element(cgen.Assign(ops_dat_access, call))
            )
    else:
        ops_dat = OPSDat("%s_dat" % function.name)
        dats[function.name] = ops_dat

        d_p_val = tuple([p[0] + h[0] for p, h in zip(function.padding, function.halo)])
        d_m_val = tuple([-(p[1] + h[1]) for p, h in zip(function.padding, function.halo)])
        dim_shape = function.shape
        base_val = [0 for i in function.shape]

        ops_decl_dat_call.append(Element(cgen.Initializer(ops_dat, Call(
            "ops_decl_dat",
            [
                block,
                1,
                dim,
                base,
                d_m,
                d_p,
                FunctionTimeAccess(function, 0),
                String(function._C_typedata),
                String(function.name)
            ],
            False
        ))))

    res.append(Expression(ClusterizedEq(Eq(dim, ListInitializer(dim_shape)))))
    res.append(Expression(ClusterizedEq(Eq(base, ListInitializer(base_val)))))
    res.append(Expression(ClusterizedEq(Eq(d_p, ListInitializer(d_p_val)))))
    res.append(Expression(ClusterizedEq(Eq(d_m, ListInitializer(d_m_val)))))
    res.extend(ops_decl_dat_call)

    return res, dats


def make_ops_ast(expr, nfops, is_Write=False):
    """
    Transform a devito expression into an OPS expression.
    Only the interested nodes are rebuilt.

    Parameters
    ----------
    expr : :class:`Node`
        Initial tree node.
    nfops : :class:`OPSNodeFactory`
        Generate OPS specific nodes.
    Returns
    -------
    :class:`Node`
        Expression alredy translated to OPS syntax.
    """

    if expr.is_Symbol:
        if expr.is_Constant:
            return nfops.new_ops_gbl(expr)
        return expr
    elif expr.is_Number:
        return expr
    elif expr.is_Indexed:
        return nfops.new_ops_arg(expr, is_Write)
    elif expr.is_Equality:
        return expr.func(
            make_ops_ast(expr.lhs, nfops, True),
            make_ops_ast(expr.rhs, nfops)
        )
    else:
        return expr.func(*[make_ops_ast(i, nfops) for i in expr.args])


def fix_ops_acc(expr, args):
    if expr.is_Symbol or expr.is_Number:
        return expr
    if expr.is_Indexed:
        return Indexed(
            expr.base,
            Macro('OPS_ACC%d(%s)' % (args.index(expr.name), expr.indices[0].name))
        )
    else:
        for i in expr.args:
            return expr.func(*[fix_ops_acc(i, args) for i in expr.args])
