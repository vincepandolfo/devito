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
