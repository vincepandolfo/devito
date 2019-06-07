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
    # Typically we end up here
    # Make a suite of cache directories based on the soname
    cache_dir.mkdir(parents=True, exist_ok=True)

    with open(h_file, 'w') as f:
        f.write("\n")
        f.write(h_code)
    with open(src_file, 'w') as f:
        f.write(code)

    ops_install_path = os.environ.get("OPS_INSTALL_PATH")
    # OPS transltation
    subprocess.run([
        "%s/../ops_translator/c/ops.py" % ops_install_path,
        "%s.%s" % (soname, compiler.src_ext)
    ], cwd=get_jit_dir())

    # CUDA kernel compilation
    cuda_install_path = os.environ.get("CUDA_INSTALL_PATH")
    subprocess.run([' '.join([
        '%s/bin/nvcc' % cuda_install_path,
        '-Xcompiler="-std=c99"',
        '-O3',
        '-gencode arch=compute_60,code=sm_60',
        '-DOPS_MPI',
        '-I%s/c/include' % ops_install_path,
        '-I.',
        '-DMPICH_IGNORE_CXX_SEEK',
        '-I/usr/include',
        '-c',
        '-o ./CUDA/%s_kernels.cu.o' % soname,
        './CUDA/%s_kernels.cu' % soname
    ])], cwd=get_jit_dir(), shell=True)

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
