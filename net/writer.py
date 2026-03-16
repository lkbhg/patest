#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: net/writer.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    writer module for patest, including asynchronous file writing functionality.
"""


from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
import asyncio
import os
import tempfile

class WriteMode(Enum):
    OVERWRITE_IF_LARGER = auto()
    CREATE_UNIQUE = auto()

@dataclass(slots=True)
class WriteTask:
    output_dir: str
    filename: str
    content: str
    mode: WriteMode



class AsyncFileWriter:
    def __init__(
        self,
        *,
        queue_size: int = 10_000,
        fsync: bool = False,
        workers: int = 1,
    ):
        self.queue = asyncio.Queue(maxsize=queue_size)
        self.fsync = fsync
        self.workers = workers
        self._tasks: list[asyncio.Task] = []
        self._stopping = False

    async def start(self):
        for _ in range(self.workers):
            self._tasks.append(
                asyncio.create_task(self._worker())
            )

    async def stop(self):
        self._stopping = True
        for _ in self._tasks:
            await self.queue.put(None)  # sentinel
        await asyncio.gather(*self._tasks)

    def submit_nowait(self, task: WriteTask) -> bool:
        if self._stopping:
            return False
        try:
            self.queue.put_nowait(task)
            return True
        except asyncio.QueueFull:
            # ⚠️ 不阻塞抓取路径
            return False
        
    async def _worker(self):
        while True:
            task = await self.queue.get()
            if task is None:
                break
            try:
                self._write(task)
            except Exception as e:
                print(f"[writer] failed: {e}")

    def _write(self, task: WriteTask):
        out_dir = Path(task.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        base = out_dir / f"{task.filename}.txt"

        if task.mode is WriteMode.CREATE_UNIQUE:
            path = base
            i = 1
            while path.exists():
                path = out_dir / f"{task.filename}_{i}.txt"
                i += 1
            self._atomic_write(path, task.content)
            return

        if task.mode is WriteMode.OVERWRITE_IF_LARGER:
            new_size = len(task.content.encode("utf-8"))
            if base.exists() and base.stat().st_size >= new_size:
                return
            self._atomic_write(base, task.content)

    def _atomic_write(self, path: Path, content: str):
        tmp_fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=path.name,
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                f.write(content)
                if self.fsync:
                    f.flush()
                    os.fsync(f.fileno())
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)





def write_file(output_dir: str, filename: str, content: str):
    output_path = Path(output_dir) / f"{filename}.txt"
    new_size = len(content.encode("utf-8"))
    # try:
    # 如果文件已存在，比较大小
    if output_path.exists():
        existing_size = output_path.stat().st_size
        if existing_size >= new_size:
            print(
                f"已有文件更大或相等，保留原文件（{existing_size} 字节），跳过写入 {new_size} 字节的新内容"
            )
            return

    # 直接写入文件并强制刷新到磁盘
    with output_path.open("w", encoding="utf-8") as f:
        f.write(content)
        f.flush()  # 刷新 Python 缓冲区
        os.fsync(f.fileno())  # 刷新操作系统缓冲区到磁盘
    # except Exception as e:
    #     return e

    # print(f"写入文件: {output_path}（{new_size} 字节）")


def write_full_file(output_dir: str, filename: str, content: str):

    output_path = Path(output_dir) / f"{filename}.txt"

    # 自动寻找可用文件名
    index = 1
    while output_path.exists():
        output_path = Path(output_dir) / f"{filename}_{index}.txt"
        index += 1

    # 写入文件并强制刷新到磁盘
    with output_path.open("w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())

   # print(f"写入文件: {output_path}")


def write_file_fast(output_dir: str, filename: str, content: str):
    output_path = Path(output_dir) / f"{filename}.txt"

    data = content.encode("utf-8")
    new_size = len(data)

    try:
        if output_path.stat().st_size >= new_size:
            return
    except FileNotFoundError:
        pass

    with output_path.open("wb") as f:
        f.write(data)