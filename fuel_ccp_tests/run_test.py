#!/usr/bin/env python

import sys

import pytest


def shell():
    if len(sys.argv) > 1:
        pytest.main(sys.argv[1:])
    else:
        pytest.main('--help')


if __name__ == '__main__':
    shell()
