from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension("_acurl", ["src/acurl.pyx"], libraries=["curl"])
]

setup(
    ext_modules=cythonize(extensions),
    setup_requires=["setuptools_scm", "cython"],
    use_scm_version={'root': '..', 'relative_to': __file__},
)
