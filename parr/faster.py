#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: parr/faster.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    faster downloader using grequests.
"""


import os
import re
import json
import time
import random
import unicodedata
import grequests
from bs4 import BeautifulSoup, Comment, Tag
from opencc import OpenCC

# ======== 读取配置 =========
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

BASE_URL      = config["base_url"]
PAGE_SUFFIX   = config["page_suffix"]
ROOT_URL      = config["root_url"]
START_PAGE    = config["start_page"]
END_PAGE      = config["end_page"]
OUTPUT_DIR    = config["output_dir"]
CONCURRENCY   = config["sem_limit"]        # 并发数，用于 grequests.map size
RETRY_ROUNDS  = config["max_retry_rounds"]
TITLE_SELECTOR   = config["title_selector"]
CONTENT_SELECTOR = config["content_selector"]
TITLE_LIMIT      = config["title_limit"]
FAILED_LOG       = os.path.join(OUTPUT_DIR, "failures.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)
cc = OpenCC('t2s')

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101"
    " Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
    " (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
    " (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

def get_random_headers():
    return {"User-Agent": random.choice(USER_AGENTS)}

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '', name).strip()

def normalize_text(text: str, convert_traditional=True, space_to_comma=False) -> str:
    if convert_traditional:
        text = cc.convert(text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r'^[\s\u3000]+|[\s\u3000]+$', '', text)
    text = re.sub(r'(?<=[\u4e00-\u9fff])[\s\u3000]+(?=[\u4e00-\u9fff])', '', text)
    text = re.sub(r'([\u4e00-\u9fff])[\s\u3000]+([A-Za-z0-9])', r'\1\2', text)
    text = re.sub(r'([A-Za-z0-9])[\s\u3000]+([\u4e00-\u9fff])', r'\1\2', text)
    text = re.sub(r'([\u4e00-\u9fff])\s+([，。！？；：,\.!?;:])', r'\1\2', text)
    text = re.sub(r'([，。！？；：,\.!?;:])\s+([\u4e00-\u9fff])', r'\1\2', text)
    text = re.sub(r'(?<=[A-Za-z])(?=[0-9])', ' ', text)
    text = re.sub(r'(?<=[0-9])(?=[A-Za-z])', ' ', text)
    def cap(m):
        w = m.group(0)
        return w[0].upper() + w[1:].lower() if any(c.isalpha() for c in w) else w
    text = re.sub(r'[A-Za-z0-9]+', cap, text)
    if space_to_comma:
        text = re.sub(r'[ \u3000]+', '，', text)
    return text

def clean_title(title: str, limit: int) -> str:
    title = re.sub(r'^\[[^\]]*\]', '', title)
    while True:
        orig = title
        for l, r in [('（','）'),('(',')'),('【','】'),
                     ('「','」'),('『','』'),('《','》')]:
            title = re.sub(
                f'^{re.escape(l)}([^{re.escape(l)}{re.escape(r)}]{{0,30}}){re.escape(r)}',
                r'\1', title
            )
        if title == orig:
            break
    title = cc.convert(title)
    conv = {'（':'(', '）':')', '【':'[', '】':']',
            '「':'"', '」':'"', '『':'"', '』':'"',
            '《':'<<', '》':'>>'}
    for f, h in conv.items():
        title = title.replace(f, h)
    title = re.sub(r'[\s\u3000]+', '', title)
    title = re.sub(r'[\\/:*?"<>|〖〗〔〕]', '', title)
    return sanitize_filename(title[:limit])

def fetch_with_retry(url: str, session=None, timeout=10):
    for _ in range(RETRY_ROUNDS):
        try:
            resp = grequests.request('GET', url,
                                     headers=get_random_headers(),
                                     timeout=timeout).send().response
            if resp and resp.status_code == 200:
                return resp.text
        except:
            time.sleep(0.1)
    return None

def extract_links_from_page(html: str, page: int) -> list:
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    trs = []
    if page == 1:
        ads = list(soup.find_all(
            string=lambda t: isinstance(t, Comment) and "广告连接" in t))
        if len(ads) >= 2:
            start, end = ads[0], ads[1]
            for e in start.find_all_next():
                if e == end: break
                if isinstance(e, Tag) and e.name == "tr":
                    cls = e.get("class") or []
                    if "tr3" in cls and "t_one" in cls:
                        trs.append(e)
    else:
        trs = soup.select("tr.tr3.t_one")
    links = []
    for tr in trs:
        a = tr.select_one("a.subject")
        if a and a.get("href"):
            href = a["href"]
            full = href if href.startswith("http") else f"{ROOT_URL.rstrip('/')}/{href.lstrip('/')}"
            links.append(full)
    return links

def parse_and_save(html: str):
    soup = BeautifulSoup(html, 'html.parser')
    ttag = soup.select_one(TITLE_SELECTOR)
    ctag = soup.select_one(CONTENT_SELECTOR)
    if not ttag or not ctag:
        return None
    raw_t = ttag.get_text()
    raw_c = ctag.get_text(separator=" ", strip=True).replace("\n","").replace("「",'"').replace("」",'"')
    t = normalize_text(raw_t, True, False)
    t = clean_title(t, TITLE_LIMIT)

    if not t.strip():  # 如果处理后的标题为空或全是空格
        t = raw_t
    t=sanitize_filename(t)

    c = normalize_text(raw_c, True, False)
    content = f"{t}\n{c}"
    path = os.path.join(OUTPUT_DIR, f"{t}.txt")
    if os.path.exists(path):
        old = open(path, 'r', encoding='utf-8').read()
        if len(content) >= len(old):
            open(path, 'w', encoding='utf-8').write(content)
    else:
        open(path, 'w', encoding='utf-8').write(content)
    return True

def main():
    # 1. 并发抓取分页链接
    page_urls = [
        BASE_URL if p == 1 else f"{BASE_URL}{PAGE_SUFFIX}{p}"
        for p in range(START_PAGE, END_PAGE + 1)
    ]
    rs = (grequests.get(u, headers=get_random_headers(), timeout=10)
          for u in page_urls)
    responses = grequests.map(rs, size=CONCURRENCY)
    links = []
    for idx, resp in enumerate(responses, START_PAGE):
        html = resp.text if resp and resp.status_code == 200 else None
        links.extend(extract_links_from_page(html, idx))

    # 2. 并发下载帖子并重试
    failed = links[:]
    for round in range(RETRY_ROUNDS):
        if not failed:
            break
        print(f"🔁 第 {round+1} 轮，总 {len(failed)} 条链接")
        rs2 = (grequests.get(u, headers=get_random_headers(), timeout=10)
               for u in failed)
        res2 = grequests.map(rs2, size=CONCURRENCY)
        new_failed = []
        for r in res2:
            if r and r.status_code == 200:
                ok = parse_and_save(r.text)
                if not ok:
                    new_failed.append(r.url)
            else:
                new_failed.append(r.url if r else None)
        failed = [u for u in new_failed if u]
    # 3. 记录未成功的
    if failed:
        with open(FAILED_LOG, 'w', encoding='utf-8') as f:
            for u in failed:
                f.write(u + "\n")
        print(f"\n❌ {len(failed)} 条链接失败，已记录到 {FAILED_LOG}")
    else:
        print("\n✅ 所有帖子下载完成。")

if __name__ == "__main__":
    main()
