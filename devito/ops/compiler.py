import os
import subprocess


from devito.compiler import get_jit_dir, get_codepy_dir


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

    subprocess.run([' '.join([
        '%s/bin/mpic++' % os.environ.get("MPI_INSTALL_PATH"),
        '-fopenmp -O3 -shared -fPIC -DUNIX -Wall -ffloat-store -g',
        '-I%s/include' % cuda_install_path,
        '-I%s/c/include' % ops_install_path,
        '-L%s/c/lib' % ops_install_path,
        '-L%s/lib64' % cuda_install_path,
        '%s_ops.cpp' % soname,
        './CUDA/%s_kernels_cu.o' % soname,
        '-lcudart -lops_cuda',
        '-o %s.so' % soname
    ])], cwd=get_jit_dir(), shell=True)
