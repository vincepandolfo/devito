from time import time
from codepy.jit import compile_from_string

import os
import subprocess
import warnings

from devito.compiler import Compiler, get_jit_dir, get_codepy_dir
from devito import configuration
from devito.logger import debug


class OPSOpenMPCompiler(Compiler):
    CC = os.environ.get('CC', 'gcc')
    CXX = os.environ.get('CXX', 'g++')
    MPICC = os.environ.get('MPICC', 'mpicc')
    MPICXX = os.environ.get('MPICXX', 'mpicxx')

    def __init__(self, *args, **kwargs):
        kwargs['cpp'] = True
        kwargs['mpi'] = True
        super(OPSOpenMPCompiler, self).__init__(*args, **kwargs)
        ops_install_path = os.environ.get('OPS_INSTALL_PATH')
        default = '-O3 -g -DUNIX -ffloat-store -fPIC -Wall'
        self.cflags = os.environ.get('CFLAGS', default).split(' ')

        self.ldflags = os.environ.get('LDFLAGS', '-shared -fopenmp').split(' ')

        include_dirs = '%s %s/c/include' % (get_jit_dir(), ops_install_path)
        self.include_dirs = include_dirs.split(' ')

        library_dirs = '%s/c/lib' % ops_install_path
        self.library_dirs = library_dirs.split(' ')

        libraries = "ops_seq stdc++"
        self.libraries = libraries.split(' ')

    def __lookup_cmds__(self):
        self.CC = 'gcc'
        self.CXX = 'g++'
        self.MPICC = 'mpicc'
        self.MPICXX = 'mpicxx'


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
    src_file = "%s.cpp" % target
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
        "%s.cpp" % soname
    ], cwd=get_jit_dir())

    if configuration.ops['target'] == 'CUDA':
        # CUDA kernel compilation
        cuda_install_path = os.environ.get("CUDA_INSTALL_PATH")
        subprocess.run([' '.join([
            '%s/bin/nvcc' % cuda_install_path,
            '-Xcompiler="-std=c99 -fPIC"',
            '-O3',
            '-gencode arch=compute_60,code=sm_60',
            '-I%s/c/include' % ops_install_path,
            '-I.',
            '-c',
            '-o ./CUDA/%s_kernels_cu.o' % soname,
            './CUDA/%s_kernels.cu' % soname
        ])], cwd=get_jit_dir(), shell=True)

        subprocess.run([' '.join([
            'g++',
            '-fopenmp -O3 -shared -fPIC -Wall -g',
            '-march=native',
            '-I%s/include' % cuda_install_path,
            '-I%s/c/include' % ops_install_path,
            '-L%s/c/lib' % ops_install_path,
            '-L%s/lib64' % cuda_install_path,
            '%s_ops.cpp' % soname,
            './CUDA/%s_kernels_cu.o' % soname,
            '-lcudart -lops_cuda',
            '-o %s.so' % soname
        ])], cwd=get_jit_dir(), shell=True)

        # removing generated cuda kernels to avoid reuse
        subprocess.run(["rm -rf ./CUDA"], cwd=get_jit_dir(), shell=True)
    elif configuration.ops['target'] == 'OpenMP':
        omp_kernel = '%s/MPI_OpenMP/%s_omp_kernels.cpp' % (get_jit_dir(), soname)
        omp_code = ""
        with open(omp_kernel, 'r') as f:
            omp_code = f.read()

        compiler = OPSOpenMPCompiler()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')

            tic = time()
            # Spinlock in case of MPI
            sleep_delay = 0 if configuration['mpi'] else 1
            _, _, _, recompiled = compile_from_string(
                compiler, target, [code, omp_code],
                [src_file, omp_kernel],
                cache_dir=cache_dir,
                debug=configuration['debug-compiler'],
                sleep_delay=sleep_delay
            )
            toc = time()

        subprocess.run(["rm -rf ./MPI_OpenMP"], cwd=get_jit_dir(), shell=True)

        if recompiled:
            debug("%s: compiled `%s` [%.2f s]" % (compiler, src_file, toc-tic))
        else:
            debug("%s: cache hit `%s` [%.2f s]" % (compiler, src_file, toc-tic))
