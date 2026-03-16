#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: config/core.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    config core module for patest, providing functions for reading and loading configuration data.
"""

from typing import Any
from .utils import *
from .struct import Networks, Treefiles, Text


def readConfig(config_path: str, readOnly=True) -> Any:
    raw_data = ConfigManager(config_path).config_data

    if readOnly == False:
        NETWORKS = ConfigDistributor(raw_data["net"])
        TREEFILES = ConfigDistributor(raw_data["treefile"])
        TEXT = ConfigDistributor(raw_data["text"])
    else:
        NETWORKS = FrozenConfigDistributor(raw_data["net"])
        TREEFILES = FrozenConfigDistributor(raw_data["treefile"])
        TEXT = FrozenConfigDistributor(raw_data["text"])

    return NETWORKS, TREEFILES, TEXT


def LoadConfig(config_path: str) -> tuple[Networks, Treefiles, Text]:
    raw_data = ConfigManager(config_path).config_data
    Net = Networks.from_json(raw_data["net"])
    Tree = Treefiles.from_json(raw_data["treefile"])
    Tex = Text.from_json(raw_data["text"])

    return Net, Tree, Tex