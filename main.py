#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: main.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    main file.
"""

from config import LoadConfig
from treefile import TreeFiles
from pathlib import Path
from net import downloader,booster,remp
import shutil


def main():

    NETWORKS, TREEFILES, TEXT = LoadConfig(config_path="config.json")

    dir_path = Path(NETWORKS.output_dir)
    reorder_path = Path(TREEFILES.reorder_dir)

    # 如果output目录存在，先整体删除
    if dir_path.exists():
        shutil.rmtree(dir_path)

    # 重新创建一个空目录
    dir_path.mkdir(parents=True, exist_ok=True)

    # 如果reorder目录存在，先整体删除
    if reorder_path.exists():
        shutil.rmtree(reorder_path)

    # 如果failed_log存在，先整体删除
    failed_log_path=Path.cwd()/Path(NETWORKS.failed_log)
    if (failed_log_path).exists():
        Path.unlink(failed_log_path)

    #downloader(NETWORKS, TEXT)
    
    # booster(NETWORKS, TEXT)
    # remp(NETWORKS, TEXT)

    # TreeFiles(TREEFILES)


if __name__ == "__main__":
    main()
