#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: single/single.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    single post fetching functionality. Simple to test the domain and the selectors. 
    Not used in the main flow, but can be useful for debugging and development.
"""

import os
import requests
from bs4 import BeautifulSoup, Comment, Tag
import re
import time
import json
from opencc import OpenCC
import unicodedata

# ======== 读取配置 =========
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

BASE_URL = config["base_url"]
PAGE_SUFFIX = config["page_suffix"]
ROOT_URL = config["root_url"]
START_PAGE = config["start_page"]
END_PAGE = config["end_page"]
OUTPUT_DIR = config["output_dir"]
SEM_LIMIT = config["sem_limit"]
RETRY_LIMIT = config["retry_limit"]
MAX_RETRY_ROUNDS = config["max_retry_rounds"]
TITLE_SELECTOR = config["title_selector"]
CONTENT_SELECTOR = config["content_selector"]
TITLE_LIMIT = config["title_limit"]
RESUME_ENABLED = config.get("resume", True)
FAILED_LOG = "failures.txt"
SLEEP_SECONDS = 1.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}

os.makedirs(OUTPUT_DIR, exist_ok=True)

cc = OpenCC('t2s')  # 繁体转简体

def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '', name).strip()

def normalize_text(text: str, convert_traditional=True, space_to_comma=False) -> str:
    if convert_traditional:
        text = cc.convert(text)

    # 全角转半角
    text = unicodedata.normalize("NFKC", text)
    
    # 删除前后空格（含全角）
    text = re.sub(r'^[\s\u3000]+', '', text)
    text = re.sub(r'[\s\u3000]+$', '', text)

    # 中文之间空格
    text = re.sub(r'(?<=[\u4e00-\u9fff])[\s\u3000]+(?=[\u4e00-\u9fff])', '', text)

    # 中文与英数之间空格
    text = re.sub(r'([\u4e00-\u9fff])[\s\u3000]+([a-zA-Z0-9])', r'\1\2', text)
    text = re.sub(r'([a-zA-Z0-9])[\s\u3000]+([\u4e00-\u9fff])', r'\1\2', text)

    # 中文与标点间空格
    text = re.sub(r'([\u4e00-\u9fff])\s+([，。！？；：,\.!?;:])', r'\1\2', text)
    text = re.sub(r'([，。！？；：,\.!?;:])\s+([\u4e00-\u9fff])', r'\1\2', text)

    # 在字母和数字之间加空格
    text = re.sub(r'(?<=[a-zA-Z])(?=[0-9])', ' ', text)
    text = re.sub(r'(?<=[0-9])(?=[a-zA-Z])', ' ', text)

    # 首字母大写（字母/数字混合词处理）
    def cap_alnum_word(m):
        word = m.group(0)
        if any(c.isalpha() for c in word):
            return word[0].upper() + word[1:].lower()
        else:
            return word
    text = re.sub(r'[a-zA-Z0-9]+', cap_alnum_word, text)

    if space_to_comma:
        text = re.sub(r'[ \u3000]+', '，', text)

    return text


import re

def clean_title(title: str, title_limit: int) -> str:
    # 1. 删除开头的 [xxx]
    title = re.sub(r'^\[[^\]]*\]', '', title)

    # 2. 删除开头括号（只删除括号本身，保留内容）
    while True:
        original = title
        for left, right in [('（', '）'), ('(', ')'),
                            ('【', '】'), ('「', '」'),
                            ('『', '』'), ('《', '》')]:
            pattern = f'^{re.escape(left)}([^{left}{right}]{{0,30}}){re.escape(right)}'
            title = re.sub(pattern, r'\1', title)
        if title == original:
            break

    # 3. 繁体转简体
    title = cc.convert(title)

    # 5. 删除所有空格（含全角空格）
    title = re.sub(r'[\s\u3000]+', '', title)

    # 6. 删除非法字符（Windows文件名限制字符）
    title = re.sub(r'[\\/:*?"<>|〖〗〔〕]', '', title)

    # 7. 限制长度
    title = title[:title_limit]

    # 8. 返回合法文件名
    return sanitize_filename(title)



def fetch_post(post_url):
    print(f"  -> 抓取帖子: {post_url}")
    try:
        res = requests.get(post_url, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'
        res.raise_for_status()
    except Exception as e:
        print(f"    请求失败: {e}")
        return

    soup = BeautifulSoup(res.text, "html.parser")
    title_tag = soup.select_one(TITLE_SELECTOR)
    content_tag = soup.select_one(CONTENT_SELECTOR)

    if not title_tag or not content_tag:
        print("    ❌ 未找到标题或正文，跳过")
        return

    raw_title = title_tag.get_text()
    raw_content = content_tag.get_text(separator=" ", strip=True)
    raw_content = raw_content.replace("\n", "").replace("「", '"').replace("」", '"')

    title = normalize_text(raw_title,convert_traditional=True, space_to_comma=False)
    title = clean_title(title, title_limit=TITLE_LIMIT)

    if not title.strip():  # 如果处理后的标题为空或全是空格
        title = raw_title
    titile=sanitize_filename(title)	

    content = normalize_text(raw_content, convert_traditional=True, space_to_comma=False)

    output_text = f"{title}\n{content}"
    filepath = os.path.join(OUTPUT_DIR, f"{title}.txt")

    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            old_text = f.read()
        if len(output_text) >= len(old_text):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(output_text)
            print(f"    ⚠️ 同名文件已覆盖（内容更长）")
        else:
            print(f"    ⏭️ 同名文件已存在，跳过")
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"    ✅ 已保存: {post_url}")


def crawl_list_page(page_num):
    url = BASE_URL if page_num == 1 else f"{BASE_URL}{PAGE_SUFFIX}{page_num}"
    print(f"\n📄 第 {page_num} 页: {url}")
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'
        res.raise_for_status()
    except Exception as e:
        print(f"请求失败: {e}")
        return

    soup = BeautifulSoup(res.text, 'html.parser')

    result_trs = []

    if page_num == 1:
        ad_comments = list(soup.find_all(string=lambda text: isinstance(text, Comment) and "广告连接" in text))
        if len(ad_comments) < 2:
            print("⚠️ 未找到两个广告注释，跳过本页")
            return
        start, end = ad_comments[0], ad_comments[1]
        for elem in start.find_all_next():
            if elem == end:
                break
            if isinstance(elem, Tag) and elem.name == "tr":
                cls = elem.get("class")
                if cls:
                    class_str = " ".join(cls) if isinstance(cls, list) else cls
                    if "tr3" in class_str and "t_one" in class_str:
                        result_trs.append(elem)
    else:
        for tr in soup.select("tr.tr3.t_one"):
            result_trs.append(tr)

    if not result_trs:
        print("⚠️ 找不到有效帖子链接")
        return

    for tr in result_trs:
        link = tr.select_one("a.subject")
        if not link:
            continue

        raw_title = link.get_text(strip=True)
        simple_title = cc.convert(raw_title)
        print(f"  🔗 标题: {simple_title}")
    
        href = link.get("href")
        if not href:
            continue
        full_url = href if href.startswith("http") else f"{ROOT_URL.rstrip('/')}/{href.lstrip('/')}"
    
        fetch_post(full_url)
        time.sleep(SLEEP_SECONDS)


def main():
    for page in range(START_PAGE, END_PAGE + 1):
        crawl_list_page(page)
        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
