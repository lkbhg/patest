#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.
"""
Project: patest
File: text/pipeline.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    text pipeline functionality.
"""


from opencc import OpenCC
from typing import Callable
from .utils import *


TITLE_RULES = {
    "wrappers": [
        ("（", "）"),
        ("(", ")"),
        ("【", "】"),
        ("「", "」"),
        ("『", "』"),
        ("《", "》"),
    ],
    "wrapper_max_len": 30,
    "symbol_map": {
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "「": '"',
        "」": '"',
        "《": "<<",
        "》": ">>",
    },
    "illegal_chars": r'[\\/:*?"<>|〖〗〔〕]',
    "max_length": 80,
}


Step = Callable[[str], str]


def run_pipeline(text: str, steps: list[Step]) -> str:
    for step in steps:
        text = step(text)
    return text


cc = OpenCC("t2s")

PIPELINE = [
    remove_square_prefix,
    lambda s: strip_wrapped_prefixes(
        s,
        wrappers=TITLE_RULES["wrappers"],
        max_len=TITLE_RULES["wrapper_max_len"],
    ),
    convert_traditional(cc),
    normalize_symbols(TITLE_RULES["symbol_map"]),
    normalize_whitespace,  # 可换策略
    remove_illegal_chars(TITLE_RULES["illegal_chars"]),
    limit_length(TITLE_RULES["max_length"]),
    sanitize_filename_step,
]


def pipeline_clean_title(title: str) -> str:
    return run_pipeline(title, PIPELINE)
