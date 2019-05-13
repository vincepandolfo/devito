import devito.types.basic as basic

__all__ = ['Array']


class Array(basic.Array):

    from_OPS = True
    is_Symbol = True

    @property
    def _C_name(self):
        return self.name


class FunctionTimeAccess(basic.Basic):
    is_LocalObject = True
    is_ArrayAccess = True

    def __init__(self, function, time_access_symbol):
        self.function = function
        self.time_access_symbol = time_access_symbol

    @property
    def _C_name(self):
        return "%s[%s]" % (self.function.name, self.time_access_symbol)

    @property
    def free_symbols(self):
        return [self.function]


class OPSDat(basic.Symbol):
    is_Symbol = True

    def get_decl_pair(self):
        return ["ops_dat"], self.name
