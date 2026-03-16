#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: parr/fastest.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    fastest downloader using grequests.
"""

import os, re, json, time, random, unicodedata, requests
from multiprocessing import Pool, cpu_count
from bs4 import BeautifulSoup, Comment, Tag
from opencc import OpenCC
from tqdm import tqdm

# ======== 读取配置 =========
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

BASE_URL        = cfg["base_url"]
PAGE_SUFFIX     = cfg["page_suffix"]
ROOT_URL        = cfg["root_url"]
START_PAGE      = cfg["start_page"]
END_PAGE        = cfg["end_page"]
OUTPUT_DIR      = cfg["output_dir"]
# 限制并发进程数：不超过用户设置、不超过CPU核数、不超过60，因为windows下限制不能超过64，linux无限制，核数多的情况下可直接设置为sem_limit
#CONCURRENCY     = min(cfg["sem_limit"] or cpu_count(), cpu_count(), 60)
CONCURRENCY     = cfg["sem_limit"]
RETRY_ROUNDS    = cfg["max_retry_rounds"]
TITLE_SELECTOR  = cfg["title_selector"]
CONTENT_SELECTOR= cfg["content_selector"]
TITLE_LIMIT     = cfg["title_limit"]
FAILED_LOG      = os.path.join("./", "failures.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)
cc = OpenCC('t2s')

USER_AGENTS = [
    # 你的 UA 列表...
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    # etc.
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
    text = re.sub(r'(?<=[\u4e00-\u9fff])[\s\u3000]+(?=[\u4e00-\u9fff])','',text)
    text = re.sub(r'([\u4e00-\u9fff])[\s\u3000]+([A-Za-z0-9])',r'\1\2',text)
    text = re.sub(r'([A-Za-z0-9])[\s\u3000]+([\u4e00-\u9fff])',r'\1\2',text)
    text = re.sub(r'([\u4e00-\u9fff])\s+([，。！？；：,\.!?;:])',r'\1\2',text)
    text = re.sub(r'([，。！？；：,\.!?;:])\s+([\u4e00-\u9fff])',r'\1\2',text)
    text = re.sub(r'(?<=[A-Za-z])(?=[0-9])',' ',text)
    text = re.sub(r'(?<=[0-9])(?=[A-Za-z])',' ',text)
    def cap(m):
        w=m.group(0)
        return w[0].upper()+w[1:].lower() if any(c.isalpha() for c in w) else w
    text = re.sub(r'[A-Za-z0-9]+', cap, text)
    if space_to_comma:
        text = re.sub(r'[ \u3000]+','，',text)
    return text

def clean_title(title: str, limit: int) -> str:
    title = re.sub(r'^\[[^\]]*\]', '', title)
    while True:
        orig = title
        for l,r in [('（','）'),('(',')'),('【','】'),
                    ('「','」'),('『','』'),('《','》')]:
            title = re.sub(
                f'^{re.escape(l)}([^{re.escape(l)}{re.escape(r)}]{{0,30}}){re.escape(r)}',
                r'\1', title
            )
        if title == orig:
            break
    title = cc.convert(title)
    conv = {'（':'(', '）':')','【':'[','】':']',
            '「':'"','」':'"','『':'"','』':'"',
            '《':'<<','》':'>>'}
    for f,h in conv.items():
        title = title.replace(f,h)
    title = re.sub(r'[\s\u3000]+','', title)
    title = re.sub(r'[\\/:*?"<>|〖〗〔〕]','', title)
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
        ads = list(soup.find_all(string=lambda t:isinstance(t,Comment) and "广告连接" in t))
        if len(ads) >= 2:
            s,e = ads[0], ads[1]
            for el in s.find_all_next():
                if el == e: break
                if isinstance(el, Tag) and el.name=="tr":
                    cls = el.get("class") or []
                    if "tr3" in cls and "t_one" in cls:
                        trs.append(el)
    else:
        trs = soup.select("tr.tr3.t_one")
    links = []
    for tr in trs:
        a=tr.select_one("a.subject")
        if a and a.get("href"):
            href=a["href"]
            full = href if href.startswith("http") else f"{ROOT_URL.rstrip('/')}/{href.lstrip('/')}"
            links.append(full)
    return links

def fetch_and_parse(url: str) -> dict:
    html = fetch_page(url)
    if not html:
        return {'url':url,'error':True}
    soup = BeautifulSoup(html,'html.parser')
    ttag=soup.select_one(TITLE_SELECTOR); ctag=soup.select_one(CONTENT_SELECTOR)
    if not ttag or not ctag:
        return {'url':url,'error':True}
    raw_t=ttag.get_text(); raw_c=ctag.get_text(separator=" ",strip=True).replace("\n","").replace("「",'"').replace("」",'"')
    t=normalize_text(raw_t,True,False)
    fname=clean_title(t,TITLE_LIMIT)


    if not fname.strip():  # 如果处理后的标题为空或全是空格
        fname = raw_t
    fname=sanitize_filename(fname)


    c=normalize_text(raw_c,True,False)
    return {'url':url,'filename':fname,'text':f"{fname}\n{c}"}

def main():
    # 1. 并发抓分页
    page_urls = [BASE_URL if p==START_PAGE else f"{BASE_URL}{PAGE_SUFFIX}{p}"
                 for p in range(START_PAGE,END_PAGE+1)]
    with Pool(CONCURRENCY) as pool:
        htmls = list(tqdm(pool.imap_unordered(fetch_page, page_urls),
                          total=len(page_urls),
                          desc="抓取分页"))

    # 2. 并发提取链接
    with Pool(CONCURRENCY) as pool:
        lists = list(tqdm(pool.imap_unordered(
            extract_links,
            zip(htmls, range(START_PAGE,END_PAGE+1))
        ), total=len(htmls), desc="提取链接"))
    links = [u for sub in lists for u in sub]

    # 3. 并发下载解析并写文件
    failed = []
    for rnd in range(RETRY_ROUNDS):
        to_do = links if rnd==0 else failed
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
                    path=os.path.join(OUTPUT_DIR, f"{res['filename']}.txt")
                    with open(path,'w',encoding='utf-8') as f:
                        f.write(res['text']); f.flush(); os.fsync(f.fileno())

    # 4. 记录失败
    if failed:
        with open(FAILED_LOG,'w',encoding='utf-8') as f:
            f.write("\n".join(failed))
        print(f"\n❌ {len(failed)} 条失败，已写入 {FAILED_LOG}")
    else:
        print("\n✅ 全部完成！")

if __name__=="__main__":
    main()
