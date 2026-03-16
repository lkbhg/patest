#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: ctext/setup.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    ctext is test module to extract content with C verision.
"""

# setup.py
from setuptools import setup
from Cython.Build import cythonize

setup(
    name="utils",
    ext_modules=cythonize("utils.pyx", compiler_directives={"language_level": "3"}),
    zip_safe=False,
)
