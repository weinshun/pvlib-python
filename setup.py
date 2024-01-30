#!/usr/bin/env python

import os

try:
    from setuptools import setup, find_namespace_packages
    from setuptools.extension import Extension
except ImportError:
    raise RuntimeError('setuptools is required')


DESCRIPTION = ('A set of functions and classes for simulating the ' +
               'performance of photovoltaic energy systems.')
LONG_DESCRIPTION = """
pvlib python is a community developed toolbox that provides a set of
functions and classes for simulating the performance of photovoltaic
energy systems and accomplishing related tasks.  The core mission of pvlib
python is to provide open, reliable, interoperable, and benchmark
implementations of PV system models.

We need your help to make pvlib-python a great tool!

Documentation: http://pvlib-python.readthedocs.io

Source code: https://github.com/pvlib/pvlib-python
"""
LONG_DESCRIPTION_CONTENT_TYPE = "text/x-rst"

DISTNAME = 'pvlib'
LICENSE = 'BSD 3-Clause'
AUTHOR = 'pvlib python Developers'
MAINTAINER_EMAIL = 'pvlib-admin@googlegroups.com'
URL = 'https://github.com/pvlib/pvlib-python'

INSTALL_REQUIRES = ['numpy >= 1.16.0',
                    'pandas >= 0.25.0',
                    'pytz',
                    'requests',
                    'scipy >= 1.5.0',
                    'h5py',
                    'importlib-metadata; python_version < "3.8"']

TESTS_REQUIRE = ['pytest', 'pytest-cov', 'pytest-mock',
                 'requests-mock', 'pytest-timeout', 'pytest-rerunfailures',
                 'pytest-remotedata', 'packaging']
EXTRAS_REQUIRE = {
    'optional': ['cython', 'ephem', 'nrel-pysam', 'numba',
                 'solarfactors', 'statsmodels'],
    'doc': ['ipython', 'matplotlib', 'sphinx == 4.5.0',
            'pydata-sphinx-theme == 0.8.1', 'sphinx-gallery',
            'docutils == 0.15.2', 'pillow',
            'sphinx-toggleprompt >= 0.0.5', 'solarfactors',
            'ephem'],
    'test': TESTS_REQUIRE
}
EXTRAS_REQUIRE['all'] = sorted(set(sum(EXTRAS_REQUIRE.values(), [])))

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Intended Audience :: Science/Research',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Topic :: Scientific/Engineering',
]

setuptools_kwargs = {
    'zip_safe': False,
    'scripts': [],
    'include_package_data': True,
    'python_requires': '>=3.7'
}

PROJECT_URLS = {
    "Bug Tracker": "https://github.com/pvlib/pvlib-python/issues",
    "Documentation": "https://pvlib-python.readthedocs.io/",
    "Source Code": "https://github.com/pvlib/pvlib-python",
}

# set up pvlib packages to be installed and extensions to be compiled

# the list of packages is not just the top-level "pvlib", but also
# all sub-packages like "pvlib.bifacial".  Here, setuptools's definition of
# "package" is, in effect, any directory you want to include in the
# distribution.  So even "pvlib.data" counts as a package, despite
# not having any python code or even an __init__.py.
# setuptools.find_namespace_packages() will find all these directories,
# although to exclude "docs", "ci", etc., we include only names matching
# the "pvlib*" glob.  Although note that "docs" does get added separately
# via the MANIFEST.in spec.
PACKAGES = find_namespace_packages(include=['pvlib*'])

extensions = []

spa_sources = ['pvlib/spa_c_files/spa.c', 'pvlib/spa_c_files/spa_py.c']
spa_depends = ['pvlib/spa_c_files/spa.h']
spa_all_file_paths = map(lambda x: os.path.join(os.path.dirname(__file__), x),
                         spa_sources + spa_depends)

if all(map(os.path.exists, spa_all_file_paths)):
    print('all spa_c files found')
    PACKAGES.append('pvlib.spa_c_files')

    spa_ext = Extension('pvlib.spa_c_files.spa_py',
                        sources=spa_sources, depends=spa_depends)
    extensions.append(spa_ext)
else:
    print('WARNING: spa_c files not detected. ' +
          'See installation instructions for more information.')


setup(name=DISTNAME,
      packages=PACKAGES,
      install_requires=INSTALL_REQUIRES,
      extras_require=EXTRAS_REQUIRE,
      tests_require=TESTS_REQUIRE,
      ext_modules=extensions,
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      long_description_content_type=LONG_DESCRIPTION_CONTENT_TYPE,
      author=AUTHOR,
      maintainer_email=MAINTAINER_EMAIL,
      license=LICENSE,
      url=URL,
      project_urls=PROJECT_URLS,
      classifiers=CLASSIFIERS,
      **setuptools_kwargs)
