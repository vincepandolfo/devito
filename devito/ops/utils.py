import cgen
import numpy as np

from collections import defaultdict, OrderedDict
from itertools import groupby

from devito import Eq
from devito.types.basic import String, SymbolicArray
from devito.ir.iet.nodes import Expression, Call, Element
from devito.ir.equations import ClusterizedEq
from devito.symbolics import ListInitializer, retrieve_indexed
from devito.ops.types import OPSStencil


def get_accesses(expr):
    mapper = defaultdict(set)
    for e in retrieve_indexed(expr, mode='all', deep=True):
        f = e.function
        accesses = []
        for a in e.indices:
            dim = a
            offset = None
            for i in a.args:
                if i.is_integer:
                    offset = i
                else:
                    dim = i

            accesses.append((dim, offset or 0))

        mapper[f].add(tuple(accesses))

    return mapper


def extend_accesses(accesses, new_accesses):
    for k, v in new_accesses.items():
        accesses[k] |= v


def generate_ops_stencils(accesses):
    function_to_stencil = defaultdict(list)
    function_to_dims = {}
    ops_stencils_initializers = []
    ops_stencils_symbols = {}

    for k, v in accesses.items():
        to_skip = -1
        if k.is_TimeFunction:
            to_skip = k._time_position
            stencils = [
                (k1, list(v1)) for k1, v1 in groupby(v, lambda s: s[k._time_position][0])
            ]

            for k1, v1 in stencils:
                name = "%s%s" % (k.name, k1)
                function_to_dims[name] = k.ndim - 1
                function_to_stencil[name].extend([
                    offset
                    for stencil in v1
                    for i, (_, offset) in enumerate(stencil) if i is not to_skip
                ])
        else:
            function_to_dims[k.name] = k.ndim
            for s in v:
                function_to_stencil[k.name].extend([
                    offset
                    for i, (_, offset) in enumerate(s)
                ])

    for f, stencil in function_to_stencil.items():
        stencil_name = "s%sd_%s_%dpt" % (
            function_to_dims[f], f, len(stencil) / function_to_dims[f]
        )

        ops_stencil_arr = SymbolicArray(
            name=stencil_name, dimensions=(len(stencil),), dtype=np.int32
        )
        ops_stencil = OPSStencil(stencil_name.upper())

        arr_assign = Eq(ops_stencil_arr, ListInitializer(stencil))

        ops_stencils_initializers.append(
            Expression(ClusterizedEq(arr_assign))
        )

        decl_call = Call("ops_decl_stencil", [
            function_to_dims[f],
            int(len(stencil) / function_to_dims[f]),
            ops_stencil_arr,
            String(ops_stencil.name)
        ])
        ops_stencils_symbols[f] = ops_stencil
        ops_stencils_initializers.append(
            Element(cgen.Initializer(ops_stencil, decl_call))
        )

    return ops_stencils_initializers, ops_stencils_symbols


# OPS Conventions
namespace = OrderedDict()

# OPS Kernel strings.
namespace['ops_acc'] = 'OPS_ACC'
namespace['ops_kernel'] = lambda i: 'Kernel%s' % i
namespace['ops_block'] = lambda i: 'block_%s' % i
namespace['ops_range'] = lambda i: 'range_%s' % i
