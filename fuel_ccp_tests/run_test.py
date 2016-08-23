#!/usr/bin/env python

import os
import sys

import pytest

import fuel_ccp_tests


def shell():
    if len(sys.argv) > 1:
        # Run py.test for fuel_ccp_tests module folder with specified options
        testpaths = os.path.dirname(fuel_ccp_tests.__file__)
        opts = ' '.join(sys.argv[1:])
        addopts = '-vvv -s -p no:django -p no:ipdb --junit-xml=nosetests.xml'
        pytest.main('{testpaths} {addopts} {opts}'.format(
            testpaths=testpaths, addopts=addopts, opts=opts))
    else:
        pytest.main('--help')


if __name__ == '__main__':
    shell()
