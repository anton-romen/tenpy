# Copyright 2018-2023 TeNPy Developers, GNU GPLv3
from setuptools import setup, Extension
try:
    from Cython.Build import cythonize
    from Cython import __version__ as cython_version
except:
    cythonize = None
    cython_version = '(not available)'
import os
import numpy
import subprocess

# hardcode version for people without git
MAJOR, MINOR, MICRO = 0, 10, 0
RELEASED = False
VERSION = '{0:d}.{1:d}.{2:d}'.format(MAJOR, MINOR, MICRO)


def get_git_revision():
    """Get revision hash from git."""
    if not os.path.exists('.git'):
        rev = "unknown"
    else:
        try:
            rev = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                          stderr=subprocess.STDOUT).decode().strip()
        except:
            rev = "unknown"
    return rev


def get_git_description():
    """Get number of commits since last git tag.
    If unknown, return 0
    """
    if not os.path.exists('.git'):
        return 0
    try:
        descr = subprocess.check_output(['git', 'describe', '--tags', '--long'],
                                        stderr=subprocess.STDOUT).decode().strip()
    except:
        return 0
    return int(descr.split('-')[1])


def get_version_info():
    full_version = VERSION
    git_rev = get_git_revision()
    if not RELEASED:
        full_version += '.dev{0:d}+{1!s}'.format(get_git_description(), git_rev[:7])
    return full_version, git_rev


def write_underscore_version_py(filename='tenpy/_version.py'):
    """Write the version at build time i.e. during compilation to file."""
    full_version, git_rev = get_version_info()
    content = """\
# THIS FILE IS GENERATED FROM setup.py
# thus, it contains the version during compilation
# Copyright 2018-2023 TeNPy Developers, GNU GPLv3
version = '{version!s}'
short_version = 'v' + version
released = {released!s}
full_version = '{full_version!s}'
git_revision = '{git_rev!s}'
numpy_version = '{numpy_ver!s}'
cython_version = '{cython_ver!s}'
"""
    content = content.format(version=VERSION,
                             full_version=full_version,
                             released=RELEASED,
                             git_rev=git_rev,
                             numpy_ver=numpy.version.full_version,
                             cython_ver=cython_version)


def setup_cython_extension():
    if cythonize is None:
        print('Could not load cython. tenpy will not be compiled.')
        return []

    include_dirs = [numpy.get_include()]
    libs = []
    lib_dirs = []
    macros = []  # C/C++ mmacros, #DEF ... in C/C++ code.
    cython_macros = {}  # Cython macros in .pyx files
    comp_direct = {  # compiler_directives
        'language_level': 3,  # use python 3
        'embedsignature': True,  # write function signature in doc-strings
    }

    # see tenpy/tools/optimization.py for details on "TENPY_OPTIMIZE"
    TENPY_OPTIMIZE = int(os.getenv("TENPY_OPTIMIZE", 1))
    if TENPY_OPTIMIZE > 1:
        comp_direct['initializedcheck'] = False
        comp_direct['boundscheck'] = False
    if TENPY_OPTIMIZE < 1:
        comp_direct['profile'] = True
        comp_direct['linetrace'] = True
    HAVE_MKL = 0
    MKL_DIR = os.getenv("MKL_DIR", os.getenv("MKLROOT", os.getenv("MKL_HOME", "")))
    if MKL_DIR:
        include_dirs.append(os.path.join(MKL_DIR, 'include'))
        lib_dirs.append(os.path.join(MKL_DIR, 'lib', 'intel64'))
        HAVE_MKL = 1
    CONDA_PREFIX = os.getenv("CONDA_PREFIX")
    if CONDA_PREFIX:
        include_dirs.append(os.path.join(CONDA_PREFIX, 'include'))
        lib_dirs.append(os.path.join(CONDA_PREFIX, 'lib'))
        if not HAVE_MKL:
            # check whether mkl-devel is installed
            HAVE_MKL = int(os.path.exists(os.path.join(CONDA_PREFIX, 'include', 'mkl.h')))
    HAVE_MKL = int(os.getenv("HAVE_MKL", HAVE_MKL))
    print("compile with HAVE_MKL =", HAVE_MKL)
    cython_macros['HAVE_MKL'] = HAVE_MKL
    if HAVE_MKL:
        libs.extend(['mkl_rt', 'pthread', 'iomp5'])
        if os.getenv("MKL_INTERFACE_LAYER", "LP64").startswith("ILP64"):
            print("using MKL interface layer ILP64 with 64-bit indices")
            macros.append(('MKL_ILP64', None))  # compile with 64-bit indices
            cython_macros['MKL_INTERFACE_LAYER'] = 1
            # the 1 is the value of `MKL_INTERFACE_ILP64` in "mkl_service.h"
            # we make sure to call mkl_set_interface_layer(MKL_INTERFACE_LAYER) in cython.
        else:
            print("using default MKL interface layer")
            cython_macros['MKL_INTERFACE_LAYER'] = 0
        # macros.append(('MKL_DIRECT_CALL', None))  # TODO: benchmark: helpfull?

    extensions = [
        Extension("*", ["tenpy/linalg/*.pyx"],
                  include_dirs=include_dirs,
                  libraries=libs,
                  library_dirs=lib_dirs,
                  define_macros=macros,
                  language='c++')
    ]
    ext_modules = cythonize(extensions,
                            compiler_directives=comp_direct,
                            compile_time_env=cython_macros)
    return ext_modules


if __name__ == '__main__':
    setup(ext_modules=setup_cython_extension())
