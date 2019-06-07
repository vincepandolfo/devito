import warnings
import os
import subprocess

from codepy.jit import compile_from_string
from time import time

from devito.logger import debug
from devito.compiler import get_jit_dir, get_codepy_dir
from devito.parameters import configuration


def jit_compile(soname, code, h_code, compiler):
    """
    JIT compile some source code given as a string.

    This function relies upon codepy's ``compile_from_string``, which performs
    caching of compilation units and avoids potential race conditions due to
    multiple processing trying to compile the same object.

    Parameters
    ----------
    soname : str
        Name of the .so file (w/o the suffix).
    code : str
        The source code to be JIT compiled.
    compiler : Compiler
        The toolchain used for JIT compilation.
    """
    target = str(get_jit_dir().joinpath(soname))
    src_file = "%s.%s" % (target, compiler.src_ext)
    h_file = "%s.h" % target

    cache_dir = get_codepy_dir().joinpath(soname[:7])
    if configuration['jit-backdoor'] is False:
        # Typically we end up here
        # Make a suite of cache directories based on the soname
        cache_dir.mkdir(parents=True, exist_ok=True)

        with open(h_file, 'w') as f:
            f.write(h_code)
        with open(src_file, 'w') as f:
            f.write(code)

        subprocess.run(
            "%s/../ops_translator/c/ops.py" % os.environ.get("OPS_INSTALL_PATH"),
            src_file
        )
    else:
        # Warning: dropping `code` on the floor in favor to whatever is written
        # within `src_file`
        try:
            with open(src_file, 'r') as f:
                code = f.read()
            # Bypass the devito JIT cache
            # Note: can't simply use Python's `mkdtemp()` as, with MPI, different
            # ranks would end up creating different cache dirs
            cache_dir = cache_dir.joinpath('jit-backdoor')
            cache_dir.mkdir(parents=True, exist_ok=True)
        except FileNotFoundError:
            raise ValueError("Trying to use the JIT backdoor for `%s`, but "
                             "the file isn't present" % src_file)

    # `catch_warnings` suppresses codepy complaining that it's taking
    # too long to acquire the cache lock. This warning can only appear
    # in a multiprocess session, typically (but not necessarily) when
    # many processes are frequently attempting jit-compilation (e.g.,
    # when running the test suite in parallel)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')

        tic = time()
        # Spinlock in case of MPI
        sleep_delay = 0 if configuration['mpi'] else 1
        _, _, _, recompiled = compile_from_string(compiler, target, code, src_file,
                                                  cache_dir=cache_dir,
                                                  debug=configuration['debug-compiler'],
                                                  sleep_delay=sleep_delay)
        toc = time()

    if recompiled:
        debug("%s: compiled `%s` [%.2f s]" % (compiler, src_file, toc-tic))
    else:
        debug("%s: cache hit `%s` [%.2f s]" % (compiler, src_file, toc-tic))
