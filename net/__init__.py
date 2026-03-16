#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: net/__init__.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    net module for patest, including downloader, booster and remp.
"""



# __init__.py
from .core import downloader
from .rem import booster
from .remp import remp

__all__ = ["downloader","booster","remp"]
