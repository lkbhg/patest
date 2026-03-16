#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: treefile/corep.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    treefile corep functionality.
"""



# treefiles_async.py
from .utils import operator
from pathlib import Path
import asyncio
from multiprocessing import Process, Manager, Value
import multiprocessing as mp
from tqdm import tqdm
from config import Treefiles
import time

# 异步 wrapper，把同步 operator 放到线程中
async def async_operator(idx, file_path, target_dir, FILES_PER_SUB, SUB_PER_PARENT, counter):
    await asyncio.to_thread(
        operator,
        idx,
        file_path,
        target_dir,
        FILES_PER_SUB,
        SUB_PER_PARENT,
    )
    # 更新全局进度
    counter.value += 1

# 每个 worker 进程运行
def worker_main(start_idx, file_chunk, TREEFILES: Treefiles, counter):
    async def run():
        sem = asyncio.Semaphore(TREEFILES.sem_threads)  # 控制 async 并发
        tasks = []

        for local_i, f in enumerate(file_chunk):
            global_i = start_idx + local_i
            tasks.append(
                async_operator(
                    global_i,
                    f,
                    Path(TREEFILES.reorder_dir),
                    TREEFILES.files_per_sub_folder,
                    TREEFILES.sub_folder_per_parent,
                    counter,
                )
            )

        # 并发执行
        await asyncio.gather(*tasks)

    asyncio.run(run())

def TreeFiles(TREEFILES: Treefiles) -> None:
    source_dir = Path(TREEFILES.source_dir)
    target_dir = Path(TREEFILES.reorder_dir)

    FILES_PER_SUB = TREEFILES.files_per_sub_folder
    SUB_PER_PARENT = TREEFILES.sub_folder_per_parent

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
            (parent_dir / str(sub_idx + 1)).mkdir(parents=True, exist_ok=True)

    # ===== 分块文件，分配进程 =====
    cpu_count = min(mp.cpu_count(),TREEFILES.process)  # 可以按 CPU 数量调整
    chunk_size = (len(file_list) + cpu_count - 1) // cpu_count
    chunks = []
    for idx, i in enumerate(range(0, len(file_list), chunk_size)):
        chunk = file_list[i:i + chunk_size]
        chunks.append((i, chunk))  # i 就是全局起始 index

    manager = Manager()
    counter = manager.Value('i', 0)  # 全局进度计数

    # 创建进程
    processes = []
    for start_idx, chunk in chunks:
        p = Process(
            target=worker_main,
            args=(start_idx, chunk, TREEFILES, counter)
        )
        p.start()
        processes.append(p)

    # 显示进度
    with tqdm(total=total_files, desc="Moving files", unit="file") as pbar:
        last_val = 0
        while any(p.is_alive() for p in processes):
            pbar.update(counter.value - last_val)
            last_val = counter.value
            time.sleep(0.5)

        # 确保全部完成
        for p in processes:
            p.join()
        pbar.update(counter.value - last_val)

    print("All files moved.")
