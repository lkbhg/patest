#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: parr/file100.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    store files in a more organized way, with subfolders.
    This version includes a post-processing step after downloading.
"""

import os
import re
import json
import time
import random
import unicodedata
import requests
import shutil
from multiprocessing import Pool, cpu_count
from bs4 import BeautifulSoup, Comment, Tag
from opencc import OpenCC
from tqdm import tqdm

# ======== 读取配置 =========
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

BASE_URL = cfg["base_url"]
PAGE_SUFFIX = cfg["page_suffix"]
ROOT_URL = cfg["root_url"]
START_PAGE = cfg["start_page"]
END_PAGE = cfg["end_page"]
OUTPUT_DIR = cfg["output_dir"]
# 限制并发进程数：不超过用户设置、不超过CPU核数、不超过60，因为windows下限制不能超过64，linux无限制，核数多的情况下可直接设置为sem_limit
# CONCURRENCY     = min(cfg["sem_limit"] or cpu_count(), cpu_count(), 60)
CONCURRENCY = cfg["sem_limit"]
RETRY_ROUNDS = cfg["max_retry_rounds"]
TITLE_SELECTOR = cfg["title_selector"]
CONTENT_SELECTOR = cfg["content_selector"]
TITLE_LIMIT = cfg["title_limit"]
FAILED_LOG = os.path.join("./", "failures.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)
cc = OpenCC('t2s')

USER_AGENTS = [
    # 你的 UA 列表...
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    # etc.
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36 OPR/26.0.1656.60",
    "Opera/8.0 (Windows NT 5.1; U; en)",
    "Mozilla/5.0 (Windows NT 5.1; U; en; rv:1.8.1) Gecko/20061208 Firefox/2.0.0 Opera 9.50",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera 9.50",
    "Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; en) Presto/2.8.131 Version/11.11",
    "Opera/9.80 (Windows NT 6.1; U; en) Presto/2.8.131 Version/11.11",
    "Opera/9.80 (Android 2.3.4; Linux; Opera Mobi/build-1107180945; U; en-GB) Presto/2.8.149 Version/11.10",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0",
    "Mozilla/5.0 (X11; U; Linux x86_64; zh-CN; rv:1.9.2.10) Gecko/20100922 Ubuntu/10.10 (maverick) Firefox/3.6.10",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv,2.0.1) Gecko/20100101 Firefox/4.0.1",
    "Mozilla/5.0 (Windows NT 6.1; rv,2.0.1) Gecko/20100101 Firefox/4.0.1",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/534.57.2 (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2",
    "MAC:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36",
    "Windows:Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50",
    "Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_3 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5",
    "Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_3 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5",
    "Mozilla/5.0 (iPad; U; CPU OS 4_3_3 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.133 Safari/534.16",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; 360SE)",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.11 TaoBrowser/2.0 Safari/536.11",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.71 Safari/537.1 LBBROWSER",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E; LBBROWSER)",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E; LBBROWSER)"
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E; QQBrowser/7.0.3698.400)",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)",
    "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.84 Safari/535.11 SE 2.X MetaSr 1.0",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; SV1; QQDownload 732; .NET4.0C; .NET4.0E; SE 2.X MetaSr 1.0)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; SE 2.X MetaSr 1.0; SE 2.X MetaSr 1.0; .NET CLR 2.0.50727; SE 2.X MetaSr 1.0)",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Maxthon/4.4.3.4000 Chrome/30.0.1599.101 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.122 UBrowser/4.0.3214.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 UBrowser/6.2.4094.1 Safari/537.36",
    "Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_3 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5",
    "Mozilla/5.0 (iPod; U; CPU iPhone OS 4_3_3 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5",
    "Mozilla/5.0 (iPad; U; CPU OS 4_2_1 like Mac OS X; zh-cn) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8C148 Safari/6533.18.5",
    "Mozilla/5.0 (iPad; U; CPU OS 4_3_3 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5",
    "Mozilla/5.0 (Linux; U; Android 2.2.1; zh-cn; HTC_Wildfire_A3333 Build/FRG83D) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
    "Mozilla/5.0 (Linux; U; Android 2.3.7; en-us; Nexus One Build/FRF91) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
    "MQQBrowser/26 Mozilla/5.0 (Linux; U; Android 2.3.7; zh-cn; MB200 Build/GRJ22; CyanogenMod-7) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
    "Opera/9.80 (Android 2.3.4; Linux; Opera Mobi/build-1107180945; U; en-GB) Presto/2.8.149 Version/11.10",
    "Mozilla/5.0 (Linux; U; Android 3.0; en-us; Xoom Build/HRI39) AppleWebKit/534.13 (KHTML, like Gecko) Version/4.0 Safari/534.13",
    "Mozilla/5.0 (BlackBerry; U; BlackBerry 9800; en) AppleWebKit/534.1+ (KHTML, like Gecko) Version/6.0.0.337 Mobile Safari/534.1+",
    "Mozilla/5.0 (hp-tablet; Linux; hpwOS/3.0.0; U; en-US) AppleWebKit/534.6 (KHTML, like Gecko) wOSBrowser/233.70 Safari/534.6 TouchPad/1.0",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0;",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)",
    "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0)",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; The World)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; TencentTraveler 4.0)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Avant Browser)",
    "Mozilla/5.0 (Linux; U; Android 2.3.7; en-us; Nexus One Build/FRF91) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
    "Mozilla/5.0 (SymbianOS/9.4; Series60/5.0 NokiaN97-1/20.0.019; Profile/MIDP-2.1 Configuration/CLDC-1.1) AppleWebKit/525 (KHTML, like Gecko) BrowserNG/7.1.18124",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS 7.5; Trident/5.0; IEMobile/9.0; HTC; Titan)",
    "UCWEB7.0.2.37/28/999",
    "NOKIA5700/ UCWEB7.0.2.37/28/999",
    "Openwave/ UCWEB7.0.2.37/28/999",
    "Openwave/ UCWEB7.0.2.37/28/999",
]


def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '', name).strip()


def normalize_text(text: str, convert_traditional=True, space_to_comma=False) -> str:
    if convert_traditional:
        text = cc.convert(text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r'^[\s\u3000]+|[\s\u3000]+$', '', text)
    text = re.sub(
        r'(?<=[\u4e00-\u9fff])[\s\u3000]+(?=[\u4e00-\u9fff])', '', text)
    text = re.sub(r'([\u4e00-\u9fff])[\s\u3000]+([A-Za-z0-9])', r'\1\2', text)
    text = re.sub(r'([A-Za-z0-9])[\s\u3000]+([\u4e00-\u9fff])', r'\1\2', text)
    text = re.sub(r'([\u4e00-\u9fff])\s+([，。！？；：,\.!?;:])', r'\1\2', text)
    text = re.sub(r'([，。！？；：,\.!?;:])\s+([\u4e00-\u9fff])', r'\1\2', text)
    text = re.sub(r'(?<=[A-Za-z])(?=[0-9])', ' ', text)
    text = re.sub(r'(?<=[0-9])(?=[A-Za-z])', ' ', text)

    def cap(m):
        w = m.group(0)
        return w[0].upper()+w[1:].lower() if any(c.isalpha() for c in w) else w
    text = re.sub(r'[A-Za-z0-9]+', cap, text)
    if space_to_comma:
        text = re.sub(r'[ \u3000]+', '，', text)
    return text


def clean_title(title: str, limit: int) -> str:
    title = re.sub(r'^\[[^\]]*\]', '', title)
    while True:
        orig = title
        for l, r in [('（', '）'), ('(', ')'), ('【', '】'),
                     ('「', '」'), ('『', '』'), ('《', '》')]:
            title = re.sub(
                f'^{re.escape(l)}([^{re.escape(l)}{re.escape(r)}]{{0,30}}){re.escape(r)}',
                r'\1', title
            )
        if title == orig:
            break
    title = cc.convert(title)
    conv = {'（': '(', '）': ')', '【': '[', '】': ']',
            '「': '"', '」': '"', '『': '"', '』': '"',
            '《': '<<', '》': '>>'}
    for f, h in conv.items():
        title = title.replace(f, h)
    title = re.sub(r'[\s\u3000]+', '', title)
    title = re.sub(r'[\\/:*?"<>|〖〗〔〕]', '', title)
    return sanitize_filename(title[:limit])


def fetch_page(url: str) -> str | None:
    for _ in range(RETRY_ROUNDS):
        try:
            r = requests.get(url, headers=get_random_headers(), timeout=10)
            if r.status_code == 200:
                return r.text
        except:
            time.sleep(0.1)
    return None


def extract_links(args):
    html, page = args
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    trs = []
    if page == START_PAGE:
        ads = list(soup.find_all(
            string=lambda t: isinstance(t, Comment) and "广告连接" in t))
        if len(ads) >= 2:
            s, e = ads[0], ads[1]
            for el in s.find_all_next():
                if el == e:
                    break
                if isinstance(el, Tag) and el.name == "tr":
                    cls = el.get("class") or []
                    if "tr3" in cls and "t_one" in cls:
                        trs.append(el)
    else:
        trs = soup.select("tr.tr3.t_one")
    links = []
    for tr in trs:
        a = tr.select_one("a.subject")
        if a and a.get("href"):
            href = a["href"]
            full = href if href.startswith(
                "http") else f"{ROOT_URL.rstrip('/')}/{href.lstrip('/')}"
            links.append(full)
    return links


def fetch_and_parse(url: str) -> dict:
    html = fetch_page(url)
    if not html:
        return {'url': url, 'error': True}
    soup = BeautifulSoup(html, 'html.parser')
    ttag = soup.select_one(TITLE_SELECTOR)
    ctag = soup.select_one(CONTENT_SELECTOR)
    if not ttag or not ctag:
        return {'url': url, 'error': True}
    raw_t = ttag.get_text()
    raw_c = ctag.get_text(separator=" ", strip=True).replace(
        "\n", "").replace("「", '"').replace("」", '"')
    t = normalize_text(raw_t, True, False)
    fname = clean_title(t, TITLE_LIMIT)

    if not fname.strip():  # 如果处理后的标题为空或全是空格
        fname = raw_t
    fname = sanitize_filename(fname)

    c = normalize_text(raw_c, True, False)
    return {'url': url, 'filename': fname, 'text': f"{fname}\n{c}"}


def organize_files(source_dir):
    DRY_RUN = False
    FILES_PER_SUB_FOLDER = 100
    SUB_FOLDER_PER_PARENT = 10
    files_lists = [f for f in os.listdir(
        source_dir) if os.path.isfile(os.path.join(source_dir, f))]
    total_files = len(files_lists)
    print(f"find {total_files} files")

    count_moved = 0
    for i, filename in enumerate(files_lists):
        sub_folder_idx = i//FILES_PER_SUB_FOLDER
        sub_folder_name = str(sub_folder_idx+1)
        parent_folder_idx = sub_folder_idx//SUB_FOLDER_PER_PARENT
        parent_folder_name = str(parent_folder_idx+1)
        target_dir = os.path.join(
            source_dir, parent_folder_name, sub_folder_name)
        src_path = os.path.join(source_dir, filename)
        dst_path = os.path.join(target_dir, filename)
        if DRY_RUN:
            print(
                f"(try DRY_RUN) move: {filename} -> / {parent_folder_name}/{sub_folder_name}/{filename}")
        else:
            os.makedirs(target_dir, exist_ok=True)
            shutil.move(src_path, dst_path)
            if (i+1) % 1000 == 0:
                print(f"moved {i+1}/{total_files} files...")


def main():
    # 1. 并发抓分页
    page_urls = [BASE_URL if p == START_PAGE else f"{BASE_URL}{PAGE_SUFFIX}{p}"
                 for p in range(START_PAGE, END_PAGE+1)]
    with Pool(CONCURRENCY) as pool:
        htmls = list(tqdm(pool.imap_unordered(fetch_page, page_urls),
                          total=len(page_urls),
                          desc="抓取分页"))

    # 2. 并发提取链接
    with Pool(CONCURRENCY) as pool:
        lists = list(tqdm(pool.imap_unordered(
            extract_links,
            zip(htmls, range(START_PAGE, END_PAGE+1))
        ), total=len(htmls), desc="提取链接"))
    links = [u for sub in lists for u in sub]

    # 3. 并发下载解析并写文件
    failed = []
    for rnd in range(RETRY_ROUNDS):
        to_do = links if rnd == 0 else failed
        if not to_do:
            break
        failed = []
        with Pool(CONCURRENCY) as pool:
            for res in tqdm(pool.imap_unordered(fetch_and_parse, to_do),
                            total=len(to_do),
                            desc=f"下载帖子 R{rnd+1}"):
                if res.get('error'):
                    failed.append(res['url'])
                else:
                    path = os.path.join(OUTPUT_DIR, f"{res['filename']}.txt")
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(res['text'])
                        f.flush()
                        os.fsync(f.fileno())

    # 4. 记录失败
    if failed:
        with open(FAILED_LOG, 'w', encoding='utf-8') as f:
            f.write("\n".join(failed))
        print(f"\n❌ {len(failed)} 条失败，已写入 {FAILED_LOG}")
    else:
        print("\n✅ 全部完成！")


if __name__ == "__main__":
    main()
