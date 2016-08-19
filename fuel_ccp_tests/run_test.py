#!/usr/bin/env python

import os
import sys

import pytest

import fuel_ccp_tests


def shell():
    if len(sys.argv) > 1:
        # Run py.test for ./fuel_ccp_tests folder with specified options
        pytest.main([os.path.dirname(fuel_ccp_tests.__file__)] + sys.argv[1:])
    else:
        pytest.main('--help')


if __name__ == '__main__':
    shell()
