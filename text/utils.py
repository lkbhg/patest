#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.
"""
Project: patest
File: text/utils.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    text utils functionality.
"""


import re
from opencc import OpenCC
import unicodedata


def normalize_clean(text: str, convert_traditional=True, space_to_comma=False) -> str:
    if convert_traditional:
        cc = OpenCC("t2s")
        text = cc.convert(text)
    # 如果 convert_traditional 为 True：
    # 使用 OpenCC 库创建一个繁体到简体的转换器 "t2s"。
    # 将 text 中的繁体字转换为简体字。
    # 作用：统一中文字符为简体，便于后续处理

    text = unicodedata.normalize("NFKC", text)
    # 全角字符转换为半角，并合并可分解字符

    # 删除 PUA 字符
    text = re.sub(r'[\uE000-\uF8FF]', '', text)


    text = re.sub(r"^[\s\u3000]+|[\s\u3000]+$", "", text)
    # 使用正则去除字符串开头和结尾的空白字符：\s：普通空格、制表符等。\u3000：全角空格。
    # 作用：去掉文本首尾的空白和全角空格

    text = re.sub(r"(?<=[\u4e00-\u9fff])[\s\u3000]+(?=[\u4e00-\u9fff])", "", text)
    # 去掉中文字符之间的空格或全角空格：(?<=[\u4e00-\u9fff])：前面是中文。
    # (?=[\u4e00-\u9fff])：后面是中文。中间的空格或全角空格被替换为空。
    # 作用：避免中文字符之间出现无意义的空格。

    text = re.sub(r"([\u4e00-\u9fff])[\s\u3000]+([A-Za-z0-9])", r"\1\2", text)
    # 去掉中文和紧跟其后的英文/数字之间的空格。
    # 示例：
    # "中文 A" → "中文A"

    text = re.sub(r"([A-Za-z0-9])[\s\u3000]+([\u4e00-\u9fff])", r"\1\2", text)
    # 去掉英文/数字和紧跟其后的中文之间的空格。
    # 示例：
    # "A 中文" → "A中文"

    text = re.sub(r"([\u4e00-\u9fff])\s+([，。！？；：,\.!?;:])", r"\1\2", text)
    # 去掉中文字符和紧随其后的标点之间的空格。
    # 示例：
    # "中文 ！" → "中文！"

    text = re.sub(r"([，。！？；：,\.!?;:])\s+([\u4e00-\u9fff])", r"\1\2", text)
    # 去掉标点和紧随其后的中文字符之间的空格。
    # 示例：
    # "！ 中文" → "！中文"

    text = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", text)
    text = re.sub(r"(?<=[0-9])(?=[A-Za-z])", " ", text)
    # 在字母和数字之间插入空格，使其更易读。
    # 示例：
    # "A123" → "A 123"
    # "123A" → "123 A"

    def cap(m):
        w = m.group(0)
        return w[0].upper() + w[1:].lower() if any(c.isalpha() for c in w) else w

    # 定义一个内部函数 cap：
    # 对匹配的单词 w：
    # 如果包含字母：
    # 将首字母大写，其余字母小写（类似标题化首字母）。
    # 否则保持不变。
    # 用于英文和数字混合单词的规范化。

    text = re.sub(r"[A-Za-z0-9]+", cap, text)
    # 对文本中连续的英文字母或数字（单词）应用 cap 函数。
    # 示例：
    # "hello WORLD123" → "Hello World123"

    if space_to_comma:
        text = re.sub(r"[ \u3000]+", "，", text)
    # 如果 space_to_comma=True：
    # 将所有空格（半角或全角）替换为中文逗号。
    # 作用：用于特定场景下用逗号分隔词。

    return text


# 全部删除Windows 文件系统中非法的文件名字符。
# 去除文件名首尾空白字符
def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "", name).strip()


def clean_title(title: str, limit: int) -> str:
    cc = OpenCC("t2s")
    title = cc.convert(title)
    # 使用 OpenCC 库创建一个繁体到简体的转换器 "t2s"。
    # 将 text 中的繁体字转换为简体字。
    # 作用：统一中文字符为简体，便于后续处理

    # title = re.sub(r"^\[[^\]]*\]", "", title)
    # 正则含义：
    # ^：字符串开头
    # \[：字面量 [
    # [^\]]*：任意数量的“非 ] 字符”
    # \]：字面量 ]
    # 删除 标题最前面的 [xxx] 标签。
    # 示例："[完结] 小说标题" → " 小说标题"


    # while True:
    #     orig = title
    #     for l, r in [
    #         ("（", "）"),
    #         ("(", ")"),
    #         ("【", "】"),
    #         ("「", "」"),
    #         ("『", "』"),
    #         ("《", "》"),
    #     ]:
    #         title = re.sub(
    #             f"^{re.escape(l)}([^{re.escape(l)}{re.escape(r)}]{{0,30}}){re.escape(r)}",
    #             r"\1",
    #             title,
    #         )
    #     if title == orig:
    #         break
    # 循环多层嵌套剥离括号
    # （剧场版）进击的巨人 → 剧场版进击的巨人
    # 【合集】某某标题     → 合集某某标题
    # 【完结】【修正版】标题

    title=re.sub(r"[\[\]【】「」『』《》]", "", title)
    #简单处理，只删除一些特殊括号
    #存在冗余，暂不处理

    conv = {
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "「": '"',
        "」": '"',
        "『": '"',
        "』": '"',
        #        "《": "<<",
        #       "》": ">>",
    }
    for f, h in conv.items():
        title = title.replace(f, h)

    # 定义一组 符号映射表：
    # 中文括号 → 英文括号
    # 中文引号 → "
    # 中文书名号 → << >>
    # 目的：
    # 统一字符集
    # 提高文件名 / 标题的跨平台兼容性

    title = re.sub(r"[\s\u3000]+", "", title)
    # 删除：普通空白,全角空格
    # 使标题成为 紧凑字符串，非常适合文件名。

    title = re.sub(r'[\\/:*?"<>|〖〗〔〕]', "", title)
    # 删除：Windows 非法字符
    # 一些不常用的中文括号

    # title[:limit]
    # 截断标题长度，防止文件名过长
    # sanitize_filename(...)
    # 再次确保 绝对安全的文件名
    return sanitize_filename(title[:limit])


#1️⃣ 去除 [xxx] 前缀
def remove_square_prefix(text: str) -> str:
    return re.sub(r"^\[[^\]]*\]", "", text)


#2️⃣ 剥离多层短括号前缀（核心规则）,这个 step 已经具备配置能力（wrappers + max_len）。
def strip_wrapped_prefixes(
    text: str,
    wrappers: list[tuple[str, str]],
    max_len: int = 30,
) -> str:
    while True:
        orig = text
        for l, r in wrappers:
            text = re.sub(
                f"^{re.escape(l)}([^{re.escape(l)}{re.escape(r)}]{{0,{max_len}}}){re.escape(r)}",
                r"\1",
                text,
            )
        if text == orig:
            break
    return text

#3️⃣ 繁体 → 简体
def convert_traditional(cc):
    def step(text: str) -> str:
        return cc.convert(text)
    return step

#4️⃣ 符号统一
def normalize_symbols(symbol_map: dict[str, str]):
    def step(text: str) -> str:
        for k, v in symbol_map.items():
            text = text.replace(k, v)
        return text
    return step

#5️⃣ 空白处理（可替换策略）
def normalize_whitespace(text: str) -> str:
    return re.sub(r"[\s\u3000]+", " ", text).strip()

#6️⃣ 删除非法字符
def remove_illegal_chars(pattern: str):
    regex = re.compile(pattern)

    def step(text: str) -> str:
        return regex.sub("", text)

    return step

#7️⃣ 长度限制 + 文件名安全
def limit_length(n: int):
    def step(text: str) -> str:
        return text[:n]
    return step


def sanitize_filename_step(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "", text).strip()

