#
# This file is part of python-corosync. Python-Corosync is free software
# that is made available under the MIT license. Consult the file "LICENSE"
# that is distributed together with this file for the exact licensing terms.
#
# Python-Corosync is copyright (c) 2008 by the python-corosync authors. See
# the file "AUTHORS" for a complete overview.

import os
import stat
from setuptools import setup, Extension


def find_corosync():
    """Find the corosync library path."""
    for path in ('/usr/lib64/corosync', '/usr/lib/corosync'):
	try:
	    st = os.stat(path)
	except:
	    st = None
	if st and stat.S_ISDIR(st.st_mode):
	    return path

library_dirs = [find_corosync()]

setup(
    name = 'python-corosync',
    version = '0.8',
    description = 'Corosync bindings for Python',
    author = 'Geert Jansen',
    author_email = 'geert@boskant.nl',
    url = 'http://code.google.com/p/python-corosync',
    license = 'MIT',
    classifiers = ['Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python'],
    package_dir = {'': 'lib'},
    packages = ['corosync'],
    ext_modules = [Extension('corosync._cpg', ['lib/corosync/_cpg.c'],
                             libraries=['cpg'], library_dirs=library_dirs)],
    test_suite = 'nose.collector'
)
