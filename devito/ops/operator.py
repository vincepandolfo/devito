from devito.logger import warning
from devito.ir.iet import (CGen, iet_insert_casts, iet_insert_decls, find_affine_trees,
                           Transformer)
from devito.ir.iet.nodes import Call, List, MetaCall
from devito.operator import Operator
from devito.ops.transformer import opsit
from devito.ops.compiler import jit_compile
from devito.types.basic import FunctionPointer

__all__ = ['OperatorOPS']


class OperatorOPS(Operator):

    """
    A special Operator generating and executing OPS code.
    """

    def __init__(self, *args, **kwargs):
        self._header_functions = []
        super().__init__(*args, **kwargs)

    def _specialize_iet(self, iet, **kwargs):
        mapper = {}

        self._includes.append('ops_seq.h')

        ops_init = Call("ops_init", [0, 0, 2])
        ops_timing = Call("ops_timing_output", [FunctionPointer("stdout")])
        ops_exit = Call("ops_exit")

        global_declarations = []
        dims = None
        for n, (section, trees) in enumerate(find_affine_trees(iet).items()):
            callable_kernel, declarations, par_loop_call_block, dims = opsit(trees, n)
            global_declarations.extend(declarations)

            self._header_functions.append(callable_kernel)
            mapper[trees[0].root] = par_loop_call_block
            mapper.update({i.root: mapper.get(i.root) for i in trees})  # Drop trees

        self._headers.append('#define OPS_%sD' % dims)
        warning("The OPS backend is still work-in-progress")

        global_declarations.append(Transformer(mapper).visit(iet))

        return List(body=[ops_init, *global_declarations, ops_timing, ops_exit])

    def _finalize(self, iet, parameters):
        iet = iet_insert_decls(iet, parameters)
        iet = iet_insert_casts(iet, parameters)

        # Now do the same to each ElementalFunction
        for k, (root, local) in list(self._func_table.items()):
            if local:
                body = iet_insert_decls(root.body, root.parameters)
                body = iet_insert_casts(body, root.parameters)
                self._func_table[k] = MetaCall(root._rebuild(body=body), True)

        for i, f in enumerate(self._header_functions):
            body = iet_insert_decls(f.body, f.parameters)
            self._header_functions[i] = f._rebuild(body=body)

        return iet

    @property
    def h_ccode(self):
        header_block = List(body=self._header_functions)
        return CGen().visit(header_block)

    def _compile(self):
        self._includes.append('%s.h' % self._soname)
        if self._lib is None:
            jit_compile(self._soname, str(self.ccode), str(self.h_ccode), self._compiler)
