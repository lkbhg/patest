#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: treefile/utils.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    treefile utils.
"""

from pathlib import Path
import shutil


def operator(
    i: int,
    file_path: Path,
    source_dir: Path,
    files_per_sub: int,
    sub_per_parent: int,
):
    parent_idx = (i // files_per_sub) // sub_per_parent
    sub_idx = (i // files_per_sub) % sub_per_parent

    target_dir = source_dir / str(parent_idx + 1) / str(sub_idx + 1)

    #shutil.move(file_path, target_dir / file_path.name)
    #shutil.copy2(file_path, target_dir / file_path.name) #with time
    shutil.copy(file_path, target_dir / file_path.name) #no time



# from dataclasses import dataclass

# @dataclass(frozen=True, slots=True)
# class TreeFilesConfig:
#     files_per_sub_folder: int
#     sub_folder_per_parent: int

#     def __post_init__(self):
#         if self.files_per_sub_folder <= 0:
#             raise ValueError("files_per_sub_folder must be > 0")
#         if self.sub_folder_per_parent <= 0:
#             raise ValueError("sub_folder_per_parent must be > 0")

# # JSON 数据
# json_str = '{"files_per_sub_folder": 1000, "sub_folder_per_parent": 100}'
# data = json.loads(json_str)

# # 直接解包
# config = TreeFilesConfig(**data)
# print(config)
