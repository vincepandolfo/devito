from devito.ir.iet import (ArrayCast, Call, Callable, Iteration, List, FindSymbols,
                           FindNodes, derive_parameters, iet_insert_C_decls)

__all__ = ['make_efunc']


class ElementalFunction(Callable):

    """
    A Callable performing a computation over an abstract convex iteration space.

    A Call to an ElementalFunction will "instantiate" such iteration space by
    supplying bounds and step increment for each Dimension listed in
    ``dynamic_dims``.
    """

    def __init__(self, name, body, retval, dynamic_dims, parameters=None,
                 prefix=('static', 'inline')):
        super(ElementalFunction, self).__init__(name, body, retval, parameters, prefix)
        self._dynamic_dims = dynamic_dims

    def make_call(self, dynamic_dims_mapper):
        from IPython import embed; embed()


def make_efunc(name, iet, retval='void', prefix='static'):
    """
    Create an ElementalFunction from (a sequence of) perfectly nested Iterations.
    """
    items = FindSymbols().visit(iet)

    # Insert array casts
    casts = [ArrayCast(i) for i in items if i.is_Tensor]
    iet = List(body=casts + [iet])

    # Insert declarations
    external = [i for i in items if i.is_Array]
    iet = iet_insert_C_decls(iet, external)

    # The Callable parameters
    params = derive_parameters(iet)

    return ElementalFunction(name, iet, retval, params, prefix)
