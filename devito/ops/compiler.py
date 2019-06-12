from time import time
from codepy.jit import compile_from_string, link_extension

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


class OPSCUDACompiler(Compiler):
    CC = os.environ.get('CC', 'nvcc')

    def __init__(self, *args, **kwargs):
        super(OPSOpenMPCompiler, self).__init__(*args, **kwargs)

        ops_install_path = os.environ.get('OPS_INSTALL_PATH')
        cuda_install_path = os.environ.get('CUDA_INSTALL_PATH')

        self.cc = '%s/bin/nvcc' % cuda_install_path

        self.cflags = ['-O3', '-XCompiler="-std=c99 -fPIC"']
        self.ldflags = []

        include_dirs = '%s %s/c/include' % (get_jit_dir(), ops_install_path)
        self.include_dirs = include_dirs.split(' ')

    def __lookup_cmds__(self):
        self.CC = 'nvcc'


class OPSCudaStep2Compiler(Compiler):
    CC = os.environ.get('CC', 'gcc')
    CXX = os.environ.get('CXX', 'g++')
    MPICC = os.environ.get('MPICC', 'mpicc')
    MPICXX = os.environ.get('MPICXX', 'mpicxx')

    def __init__(self, *args, **kwargs):
        kwargs['cpp'] = True
        kwargs['mpi'] = True
        super(OPSOpenMPCompiler, self).__init__(*args, **kwargs)
        ops_install_path = os.environ.get('OPS_INSTALL_PATH')
        cuda_install_path = os.environ.get('CUDA_INSTALL_PATH')

        cflags = '-O3 -shared -fopenmp -fPIC -Wall'
        self.cflags = os.environ.get('CFLAGS', cflags).split(' ')

        self.ldflags = os.environ.get('LDFLAGS', '').split(' ')

        include_dirs = '%s/include %s/c/include' % (cuda_install_path, ops_install_path)
        self.include_dirs = include_dirs.split(' ')

        library_dirs = '%s/lib64 %s/c/lib' % (cuda_install_path, ops_install_path)
        self.library_dirs = library_dirs.split(' ')

        libraries = "ops_cuda cudart"
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

    ops_src = '%s/%s_ops.cpp' % (get_jit_dir(), soname)
    with open(ops_src, 'r') as f:
        code = f.read()

    if configuration.ops['target'] == 'CUDA':
        # CUDA kernel compilation
        cuda_compiler = OPSCUDACompiler()
        cuda_src = '%s/CUDA/%s_kernels.cu' % (get_jit_dir(), soname)
        cuda_target = '%s/%s_kernels_cu' % (get_jit_dir(), soname)

        cuda_code = ""
        with open(cuda_src, 'r') as f:
            cuda_code = f.read()

        cuda_step2_compiler = OPSCudaStep2Compiler()

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')

            # Spinlock in case of MPI
            sleep_delay = 0 if configuration['mpi'] else 1
            _, _, cuda_o, recompiled = compile_from_string(
                cuda_compiler, cuda_target,
                cuda_code, cuda_src,
                cache_dir=cache_dir,
                debug=configuration['debug-compiler'],
                sleep_delay=sleep_delay,
                object=True
            )

            _, _, src_o, recompiled = compile_from_string(
                cuda_step2_compiler, target,
                code, src_file,
                cache_dir=cache_dir,
                debug=configuration['debug-compiler'],
                sleep_delay=sleep_delay,
                object=True
            )

            link_extension(
                cuda_step2_compiler,
                [cuda_o, src_o],
                target,
                cache_dir=cache_dir,
                debug=configuration['debug-compiler']
            )

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
