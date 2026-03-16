#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: config/utils.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    config structure utility functions
"""


import json
from typing import Any


# ======== 读取配置 =========
class ConfigManager:
    def __init__(self, config_path: str = "config.json") -> None:
        self._config_path = config_path
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self.config_data = json.load(f)
        except FileNotFoundError:
            raise Exception(f"file {self._config_path} not found")
        except json.JSONDecodeError:
            raise Exception(f"format of {self._config_path} is wrong")
        

class ConfigDistributor:
    def __init__(self,input:Any) -> None: 
        for key, value in input.items():
            # attr_name = key.upper()
            attr_name = key
            setattr(self, attr_name, value)


class FrozenConfigDistributor:
    def __init__(self,input:Any) -> None: 
        for key, value in input.items():
            # attr_name = key.upper()
            attr_name = key
            object.__setattr__(self, attr_name, value)

    def __getattribute__(self, name: str) -> Any:
        return object.__getattribute__(self, name)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Config is read-only")


