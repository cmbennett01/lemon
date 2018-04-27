#! /usr/bin/env python2

# Copyright (c) 2012 Victor Terron. All rights reserved.
# Institute of Astrophysics of Andalusia, IAA-CSIC
#
# This file is part of LEMON.
#
# LEMON is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""
This is a convenience script for finding all the unit tests in the ./test/
directory and running them. Test modules are automatically detected, using
TestLoader.discover(), which loads the test files that match the Unix-shell
pattern 'test*.py' (such as ./test/test_passband.py).

"""

import sys
from test import unittest

# This import checks whether the FITS images used by some tests are where
# expected and, if that is not the case, automatically downloads them from the
# STScI Digitized Sky Survey. In this manner, any image retrieval will be done
# before running the unit tests, never halfway through their execution.
import test.dss_images

TESTS_PACKAGE = 'test'

if __name__ == "__main__":

    loader = unittest.TestLoader()
    tests = loader.discover(TESTS_PACKAGE)
    runner = unittest.runner.TextTestRunner(verbosity = 2)
    runner.failfast = True
    result = runner.run(tests)
    sys.exit(not result.wasSuccessful())

