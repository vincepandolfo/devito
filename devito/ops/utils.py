from collections import defaultdict, OrderedDict

from devito.symbolics import retrieve_indexed


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


# OPS Conventions
namespace = OrderedDict()

# OPS Kernel strings.
namespace['ops_acc'] = 'OPS_ACC'
namespace['ops_kernel'] = lambda i: 'Kernel%s' % i
