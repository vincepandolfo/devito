from devito.tools import dtype_to_cstr

import devito.types.basic as basic
import devito.types.constant as constant

__all__ = ['Array']


class Array(basic.Array):

    from_OPS = True
    is_Symbol = True

    def __init__(self, is_Write, *args, **kwargs):
        self.is_Write = is_Write
        super().__init__(args, kwargs)

    @property
    def _C_name(self):
        return self.name

    @property
    def _C_typename(self):
        if self.is_Write:
            return super()._C_typename

        return "const %s" % super()._C_typename


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


class OPSStencil(basic.Symbol):
    is_Symbol = True

    def get_decl_pair(self):
        return ["ops_stencil"], self.name


class OPSBlock(basic.Symbol):
    is_Symbol = True

    def get_decl_pair(self):
        return ["ops_block"], self.name


class OPSArg(basic.Symbol):
    is_Symbol = True

    def get_decl_pair(self):
        return ["ops_arg"], self.name


class ConstantDereference(constant.Constant):

    @property
    def _C_name(self):
        return '*%s' % self.name

    @property
    def _C_typename(self):
        return '%s%s*' % ('const ' if self.is_const else '',
                          dtype_to_cstr(self.dtype))
