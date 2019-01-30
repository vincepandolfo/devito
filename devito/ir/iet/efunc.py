from devito.ir.iet import (ArrayCast, Call, Callable, Iteration, List, FindSymbols,
                           FindNodes, derive_parameters, iet_insert_C_decls)

__all__ = ['make_efunc']


class ElementalFunction(Callable):
    """
    A Callable performing a computation over a convex iteration space.

    The iteration space is implemented as (a sequence of) perfectly
    nested Iterations.
    """

    def __init__(self, name, body, retval, parameters, prefix=('static', 'inline')):
        super(ElementalFunction, self).__init__(name, body, retval, parameters, prefix)

        self._mapper = {}
        for i in FindNodes(Iteration).visit(body):
            try:
                self._mapper[i.dim] = (self.parameters.index(i.dim.symbolic_min),
                                       self.parameters.index(i.dim.symbolic_max))
            except ValueError:
                pass

    def make_call(self, subs):
        pass


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
