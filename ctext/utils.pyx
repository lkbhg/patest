# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: ctext/utils.pyx
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    this is an auto-gen temp file
"""

# text_cy.pyx
# cython: language_level=3
import re
import unicodedata
from opencc import OpenCC
from config import Text


# 全局初始化 OpenCC 对象（避免每次调用都创建）
cc_global = OpenCC("t2s")

# 预编译正则
RE_SPACE_EDGE = re.compile(r"^[\s\u3000]+|[\s\u3000]+$")
RE_CN_SPACE = re.compile(r"(?<=[\u4e00-\u9fff])[\s\u3000]+(?=[\u4e00-\u9fff])")
RE_CN_EN = re.compile(r"([\u4e00-\u9fff])[\s\u3000]+([A-Za-z0-9])")
RE_EN_CN = re.compile(r"([A-Za-z0-9])[\s\u3000]+([\u4e00-\u9fff])")
RE_CN_PUNCT = re.compile(r"([\u4e00-\u9fff])\s+([，。！？；：,\.!?;:])")
RE_PUNCT_CN = re.compile(r"([，。！？；：,\.!?;:])\s+([\u4e00-\u9fff])")
RE_WORD = re.compile(r"[A-Za-z0-9]+")


def normalize_clean(text: str, convert_traditional=True, space_to_comma=False) -> str:
    """
    高性能文本清洗 + 繁简转换
    """
    if convert_traditional:
        text = cc_global.convert(text)

    text = unicodedata.normalize("NFKC", text)
    text = RE_SPACE_EDGE.sub("", text)
    text = RE_CN_SPACE.sub("", text)
    text = RE_CN_EN.sub(r"\1\2", text)
    text = RE_EN_CN.sub(r"\1\2", text)
    text = RE_CN_PUNCT.sub(r"\1\2", text)
    text = RE_PUNCT_CN.sub(r"\1\2", text)

    # 在字母和数字之间插入空格
    text = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", text)
    text = re.sub(r"(?<=[0-9])(?=[A-Za-z])", " ", text)

    # 首字母大写
    def cap(m):
        w = m.group(0)
        return w[0].upper() + w[1:].lower() if any(c.isalpha() for c in w) else w

    text = RE_WORD.sub(cap, text)

    if space_to_comma:
        text = re.sub(r"[ \u3000]+", "，", text)

    return text


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "", name).strip()


def clean_title(title: str, limit: int) -> str:
    title = cc_global.convert(title)
    title = re.sub(r"[\[\]【】「」『』《》]", "", title)
    conv = {
        "（": "(", "）": ")", "【": "[", "】": "]",
        "「": '"', "」": '"', "『": '"', "』": '"'
    }
    for k, v in conv.items():
        title = title.replace(k, v)
    title = re.sub(r"[\s\u3000]+", "", title)
    title = re.sub(r'[\\/:*?"<>|〖〗〔〕]', "", title)
    return sanitize_filename(title[:limit])


def content(input: str) -> str:
    return normalize_clean(input, convert_traditional=True, space_to_comma=False)


def title(input: str, TEXT: Text) -> str:
    output = clean_title(input,TEXT.title_limit)
    if not output:
        output = sanitize_filename(input)
    return output

