import cgen
import numpy as np

from devito import Eq
from devito.ir.equations import ClusterizedEq
from devito.ir.iet import Call, Element, Expression, FindNodes, List
from devito.ops.node_factory import OPSNodeFactory
from devito.ops.nodes import OPSKernel
from devito.ops.types import OPSDat, FunctionTimeAccess
from devito.ops.utils import namespace
from devito.types.basic import Symbol, SymbolicArray, String
from devito.symbolics.extended_sympy import Byref, ListInitializer


def opsit(trees, count):
    node_factory = OPSNodeFactory()
    expressions = []
    parameters = set()
    constants = []
    to_remove = []
    for tree in trees:
        expressions.extend(FindNodes(Expression).visit(tree.inner))

    ops_expressions = []

    for i in reversed(expressions):
        parameters |= set(i.functions)
        ops_expressions.insert(0, Expression(make_ops_ast(i.expr, node_factory)))
        constants.extend([c for c in i.functions if c.is_Constant])

        if i.is_scalar_assign:
            to_remove.append(i.write)

    parameters -= set(to_remove)
    arguments = set()
    to_remove = []

    for exp in ops_expressions:
        func = [f for f in exp.functions if f.name != "OPS_ACC_size"]
        arguments |= set(func)
        if exp.is_scalar_assign:
            to_remove.append(exp.write)

    arguments -= set(to_remove)

    callable_kernel = OPSKernel(
        namespace['ops_kernel'](count),
        ops_expressions,
        "void",
        sorted(arguments, key=lambda i: (i.is_Constant, i.name))
    )

    const_declarations = [to_ops_const(c) for c in constants]
    dat_declarations = [to_ops_dat(p) for p in parameters]

    return callable_kernel, const_declarations, List(body=dat_declarations)


def to_ops_const(function):
    return Call(
        "ops_decl_const", [
            String(function.name), 1, String(function._C_typedata), Byref(function),
        ]
    )


def to_ops_dat(function):
    if function.is_TimeFunction:
        res = []
        time_pos = function._time_position
        time_index = function.indices[time_pos]
        time_dims = function.shape[time_pos]

        dim = SymbolicArray(
            name="%s_dim" % function.name,
            dimensions=(function.ndim - 1,),
            dtype=np.int32
        )
        dim_shape = function.shape[:time_pos] + function.shape[time_pos + 1:]
        base = SymbolicArray(
            name="%s_base" % function.name,
            dimensions=(function.ndim - 1,),
            dtype=np.int32
        )

        base_val = [0 for i in range(function.ndim - 1)]
        res.append(Expression(ClusterizedEq(Eq(dim, ListInitializer(dim_shape)))))
        res.append(
            Expression(
                ClusterizedEq(Eq(
                    base,
                    ListInitializer(base_val)
                )))
        )

        for i in range(time_dims):
            access = FunctionTimeAccess(function, Symbol("%s%s" % (time_index, i)))
            ops_dat = OPSDat("%s%s%s" % (function.name, time_index, i))
            ops_decl_dat_call = Call(
                "ops_decl_dat",
                [
                    String("block"),  # TODO: this is a placeholder
                    dim,
                    base,
                    base,
                    base,
                    access,
                    String(function._C_typedata),
                    String("%s%s%s" % (function.name, time_index, i))
                ]
            )
            res.append(Element(cgen.Initializer(ops_dat, ops_decl_dat_call)))

        return res

    dim = SymbolicArray(
        name="%s_dim" % function.name,
        dimensions=(function.ndim,),
        dtype=np.int32
    )

    base = SymbolicArray(
        name="%s_base" % function.name,
        dimensions=(function.ndim,),
        dtype=np.int32
    )

    return [
        Expression(ClusterizedEq(Eq(base, ListInitializer([0 for i in function.shape])))),
        Expression(ClusterizedEq(Eq(dim, ListInitializer(function.shape)))),
        Call("ops_decl_dat", [String("block"), function.ndim, dim, function])
    ]


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
