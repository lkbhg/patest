#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: config/struct.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    config structure define
"""


from dataclasses import dataclass
from typing import TypeVar, Type, Dict
import httpx

T = TypeVar("T", bound="JsonStruct")


@dataclass
class JsonStruct:
    @classmethod
    def from_json(cls: Type[T], data: Dict) -> T:
        """从已经解析好的 dict 初始化 dataclass"""
        return cls(**data)


@dataclass
class Identity:
    headers: dict
    cookies: httpx.Cookies
    proxy: str | None = None

@dataclass
class Networks(JsonStruct):
    base_url: str
    table_suffix: str
    page_type: str
    page_suffix: str
    push_cookie_id:str
    start_page: int
    end_page: int
    process: int
    sem_threads:int
    identity_pool_size:int
    timeout:int
    retry_rounds: int
    failed_log: str
    title_selector: str
    content_selector: str
    title_limit: int
    output_dir: str


@dataclass
class Treefiles(JsonStruct):
    source_dir: str
    reorder_dir: str
    encoding: str
    process:int
    sem_threads:int
    auto_mkdir: bool
    dry_run: bool
    files_per_sub_folder: int
    sub_folder_per_parent: int


@dataclass
class Text(JsonStruct):
    title_limit: int
    lowercase: bool


# 只加载一次：
# class Config(BaseModel):
#     a: int
#     b: float

#     _instance = None

#     class Config:
#         frozen = True

#     def __init__(self, **data):
#         raise RuntimeError("Use from_json()")

#     @classmethod
#     def from_json(cls, json_str: str) -> Config:
#         if cls._instance is not None:
#             raise RuntimeError("Config already initialized")

#         obj = super().__call__(**json.loads(json_str))
#         cls._instance = obj
#         return obj
