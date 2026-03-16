#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: text/core.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    text core functionality.
"""


from .utils import normalize_clean, clean_title,sanitize_filename
from config import Text


def content(input: str) -> str:
    output=normalize_clean(input, convert_traditional=True, space_to_comma=False)
    return output


def title(input: str, TEXT: Text) -> str:
    output=clean_title(input, TEXT.title_limit)
    if not output:  # 如果处理后的标题为空或全是空格
        output = input
        output = sanitize_filename(input)
    return output
