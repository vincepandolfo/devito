import cgen
import numpy as np

from collections import defaultdict

from devito import Eq
from devito.ir.equations import ClusterizedEq
from devito.ir.iet import Call, Element, Expression, FindNodes, IterationTree, List
from devito.ops.node_factory import OPSNodeFactory
from devito.ops.nodes import OPSKernel
from devito.ops.types import OPSArg, OPSBlock, OPSDat, FunctionTimeAccess
from devito.ops.utils import (extend_accesses, generate_ops_stencils, get_accesses,
                              namespace)
from devito.tools import dtype_to_cstr
from devito.types.basic import FunctionPointer, Symbol, SymbolicArray, String
from devito.symbolics.extended_sympy import Byref, ListInitializer

OPS_WRITE = FunctionPointer("OPS_WRITE")
OPS_READ = FunctionPointer("OPS_READ")


def opsit(trees, count):
    node_factory = OPSNodeFactory()
    expressions = []
    parameters = set()
    constants = []
    to_remove = []
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
        Call("ops_decl_block", [it_dims, String(block.name)])
    ))

    ops_expressions = []
    accesses = defaultdict(set)

    for i in reversed(expressions):
        extend_accesses(accesses, get_accesses(i.expr))
        parameters |= set(i.functions)
        ops_expressions.insert(0, Expression(make_ops_ast(i.expr, node_factory)))
        constants.extend([c for c in i.functions if c.is_Constant])

        if i.is_scalar_assign:
            to_remove.append(i.write)

    ops_stencils_initializers, ops_stencils = generate_ops_stencils(accesses)

    parameters -= set(to_remove)
    arguments = set()
    to_remove = []

    for exp in ops_expressions:
        func = [f for f in exp.functions if f.name != "OPS_ACC_size"]
        arguments |= set(func)
        if exp.is_scalar_assign:
            to_remove.append(exp.write)

    arguments -= set(to_remove)
    arguments = sorted(arguments, key=lambda i: (i.is_Constant, i.name))

    callable_kernel = OPSKernel(
        namespace['ops_kernel'](count),
        ops_expressions,
        "void",
        arguments
    )

    const_declarations = [to_ops_const(c) for c in constants]
    dat_declarations = []
    argname_to_dat = {}

    for p in parameters:
        if p.is_Constant:
            continue

        dat_dec, dat_sym = to_ops_dat(p, block)
        dat_declarations.extend(dat_dec)

        for dat in dat_sym:
            argname_to_dat[dat.name.replace("_dat", "")] = dat

    par_loop_range_arr = SymbolicArray(
        name=namespace['ops_range'](count),
        dimensions=(len(it_range),),
        dtype=np.int32
    )
    par_loop_range_init = Expression(ClusterizedEq(Eq(
        par_loop_range_arr,
        ListInitializer([mx - mn for mn, mx in it_range])
    )))

    ops_args_inits, ops_args = get_ops_args(
        [a for a in arguments if not a.is_Constant], ops_stencils, argname_to_dat
    )
    print(ops_args_inits)

    par_loop = Call("ops_par_loop", [
        FunctionPointer(callable_kernel.name),
        String(callable_kernel.name),
        block,
        it_dims,
        par_loop_range_arr,
        *ops_args
    ])

    dat_declarations.extend(ops_args_inits)
    dat_declarations.append(par_loop)
    print(dat_declarations)

    return (
        callable_kernel,
        [par_loop_range_init, block_init] +
        ops_stencils_initializers +
        const_declarations,
        List(body=dat_declarations)
    )


def get_ops_args(args, stencils, name_to_dat):
    ops_args_inits = []
    ops_args = []

    for arg in args:
        ops_arg = OPSArg("%s_arg" % arg.name)
        ops_args.append(ops_arg)
        ops_args_inits.append(Element(cgen.Initializer(ops_arg, Call("ops_arg_dat", [
            name_to_dat[arg.name],
            stencils[arg.name],
            String(dtype_to_cstr(arg.dtype)),
            OPS_WRITE if arg.is_Write else OPS_READ
        ]))))

    return ops_args_inits, ops_args


def to_ops_const(function):
    return Call(
        "ops_decl_const", [
            String(function.name), 1, String(function._C_typedata), Byref(function),
        ]
    )


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

    if function.is_TimeFunction:
        res = []
        time_pos = function._time_position
        time_index = function.indices[time_pos]
        time_dims = function.shape[time_pos]

        dim_shape = function.shape[:time_pos] + function.shape[time_pos + 1:]
        base_val = [0 for i in range(ndim)]

        res.append(Expression(ClusterizedEq(Eq(dim, ListInitializer(dim_shape)))))
        res.append(Expression(ClusterizedEq(Eq(base, ListInitializer(base_val)))))

        dats = []

        for i in range(time_dims):
            access = FunctionTimeAccess(function, Symbol("%s%s" % (time_index, i)))
            ops_dat = OPSDat("%s%s%s_dat" % (function.name, time_index, i))
            ops_decl_dat_call = Call(
                "ops_decl_dat",
                [
                    block,
                    dim,
                    base,
                    base,
                    base,
                    access,
                    String(function._C_typedata),
                    String("%s%s%s" % (function.name, time_index, i))
                ]
            )
            dats.append(ops_dat)
            res.append(Element(cgen.Initializer(ops_dat, ops_decl_dat_call)))

        return res, dats

    ops_dat = OPSDat("%s_dat" % function.name)

    return [
        Expression(ClusterizedEq(Eq(base, ListInitializer([0 for i in function.shape])))),
        Expression(ClusterizedEq(Eq(dim, ListInitializer(function.shape)))),
        Element(cgen.Initializer(
            ops_dat,
            Call("ops_decl_dat", [String("block"), function.ndim, dim, function]))
        )
    ], (ops_dat,)


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

    if expr.is_Symbol or expr.is_Number:
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
