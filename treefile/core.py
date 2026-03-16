#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: treefile/core.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    treefile core functionality.
"""

from .utils import operator
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from config import Treefiles


def TreeFiles(TREEFILES: Treefiles) -> None:
    source_dir = Path(TREEFILES.source_dir)
    target_dir = Path(TREEFILES.reorder_dir)

    FILES_PER_SUB = TREEFILES.files_per_sub_folder
    SUB_PER_PARENT = TREEFILES.sub_folder_per_parent

    # 收集文件
    file_list = [p for p in source_dir.iterdir() if p.is_file()]
    total_files = len(file_list)

    print(f"find {total_files} files")

    if total_files == 0:
        return

    # 计算目录层级
    total_sub_folders = (total_files - 1) // FILES_PER_SUB + 1
    total_parent_folders = (total_sub_folders - 1) // SUB_PER_PARENT + 1

    # 创建完整目录树
    for parent_idx in range(total_parent_folders):
        parent_dir = target_dir / str(parent_idx + 1)
        for sub_idx in range(SUB_PER_PARENT):
            global_sub_idx = parent_idx * SUB_PER_PARENT + sub_idx
            if global_sub_idx >= total_sub_folders:
                break
            # (parent_dir / str(global_sub_idx + 1)).mkdir(parents=True, exist_ok=True)
            (parent_dir / str(sub_idx + 1)).mkdir(parents=True, exist_ok=True)

    # 移动文件

    with ThreadPoolExecutor(max_workers=TREEFILES.process) as executor:
        futures = [
            executor.submit(
                operator,
                i,
                file_path,
                target_dir,
                FILES_PER_SUB,
                SUB_PER_PARENT,
            )
            for i, file_path in enumerate(file_list)
        ]

        for _ in tqdm(
            as_completed(futures),
            total=total_files,
            desc="Moving files",
            unit="file",
        ):
            pass

    # with ThreadPoolExecutor(max_workers=64) as executor:
    #     for _ in tqdm(
    #         executor.map(
    #             operator,
    #             range(total_files),
    #             file_list,
    #             [target_dir] * total_files,
    #             [FILES_PER_SUB] * total_files,
    #             [SUB_PER_PARENT] * total_files,
    #         ),
    #         total=total_files,
    #         desc="Moving files",
    #         unit="file",
    #     ):
    #         pass

    print("All files moved.")
