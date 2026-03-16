#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: parr/parr.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    parr downloader using httpx and asyncio.
"""


import os
import re
import json
import httpx
import asyncio
import random
from bs4 import BeautifulSoup, Comment, Tag
from opencc import OpenCC
import unicodedata
from tqdm.asyncio import tqdm

# ======== 读取配置 =========
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

BASE_URL         = config["base_url"]
PAGE_SUFFIX      = config["page_suffix"]
ROOT_URL         = config["root_url"]
START_PAGE       = config["start_page"]
END_PAGE         = config["end_page"]
OUTPUT_DIR       = config["output_dir"]
SEM_LIMIT        = config["sem_limit"]
RETRY_LIMIT      = config["retry_limit"]
MAX_RETRY_ROUNDS = config["max_retry_rounds"]
TITLE_SELECTOR   = config["title_selector"]
CONTENT_SELECTOR = config["content_selector"]
TITLE_LIMIT      = config["title_limit"]
FAILED_LOG       = os.path.join(OUTPUT_DIR, "failures.txt")
SLEEP_SECONDS    = 1.0

os.makedirs(OUTPUT_DIR, exist_ok=True)
cc = OpenCC('t2s')

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]
def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }

def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '', name).strip()

def normalize_text(text: str, convert_traditional=True, space_to_comma=False) -> str:
    if convert_traditional:
        text = cc.convert(text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r'^[\s\u3000]+|[\s\u3000]+$', '', text)
    text = re.sub(r'(?<=[\u4e00-\u9fff])[\s\u3000]+(?=[\u4e00-\u9fff])', '', text)
    text = re.sub(r'([\u4e00-\u9fff])[\s\u3000]+([a-zA-Z0-9])', r'\1\2', text)
    text = re.sub(r'([a-zA-Z0-9])[\s\u3000]+([\u4e00-\u9fff])', r'\1\2', text)
    text = re.sub(r'([\u4e00-\u9fff])\s+([，。！？；：,\.!?;:])', r'\1\2', text)
    text = re.sub(r'([，。！？；：,\.!?;:])\s+([\u4e00-\u9fff])', r'\1\2', text)
    text = re.sub(r'(?<=[a-zA-Z])(?=[0-9])', ' ', text)
    text = re.sub(r'(?<=[0-9])(?=[a-zA-Z])', ' ', text)
    def cap_alnum_word(m):
        w = m.group(0)
        return w[0].upper()+w[1:].lower() if any(c.isalpha() for c in w) else w
    text = re.sub(r'[a-zA-Z0-9]+', cap_alnum_word, text)
    if space_to_comma:
        text = re.sub(r'[ \u3000]+', '，', text)
    return text

def clean_title(title: str, title_limit: int) -> str:
    title = re.sub(r'^\[[^\]]*\]', '', title)
    while True:
        orig = title
        for l,r in [('（','）'),('(',')'),('【','】'),('「','」'),('『','』'),('《','》')]:
            title = re.sub(
                f'^{re.escape(l)}([^{re.escape(l)}{re.escape(r)}]{{0,30}}){re.escape(r)}',
                r'\1', title
            )
        if title==orig: break
    title = cc.convert(title)
    full_to_half = {'（':'(', '）':')', '【':'[','】':']','「':'"','」':'"','『':'"','』':'"','《':'<<','》':'>>'}
    for f,h in full_to_half.items():
        title = title.replace(f,h)
    title = re.sub(r'[\s\u3000]+','', title)
    title = re.sub(r'[\\/:*?"<>|〖〗〔〕]','', title)
    return sanitize_filename(title[:title_limit])

async def fetch_html(client, url):
    for _ in range(RETRY_LIMIT):
        try:
            r = await client.get(url, headers=get_random_headers(), timeout=15)
            if r.status_code==200:
                return r.text
        except:
            await asyncio.sleep(1)
    return None

async def extract_links_page(page_sem, client, page_num):
    async with page_sem:
        url = BASE_URL if page_num==1 else f"{BASE_URL}{PAGE_SUFFIX}{page_num}"
        html = await fetch_html(client, url)
        if not html: return []
        soup = BeautifulSoup(html,'html.parser')
        trs = []
        if page_num==1:
            ads = list(soup.find_all(string=lambda t:isinstance(t,Comment) and "广告连接" in t))
            if len(ads)>=2:
                start,end = ads[0],ads[1]
                for e in start.find_all_next():
                    if e==end: break
                    if isinstance(e,Tag) and e.name=="tr":
                        cls=e.get("class") or []
                        if "tr3" in cls and "t_one" in cls:
                            trs.append(e)
        else:
            trs = soup.select("tr.tr3.t_one")
        links=[]
        for tr in trs:
            a = tr.select_one("a.subject")
            if a and a.get("href"):
                href=a["href"]
                links.append(href if href.startswith("http") else f"{ROOT_URL.rstrip('/')}/{href.lstrip('/')}")
        return links

async def fetch_post_page(post_sem, client, url):
    async with post_sem:
        html = await fetch_html(client, url)
    if not html: return url
    soup=BeautifulSoup(html,"html.parser")
    ttag=soup.select_one(TITLE_SELECTOR); ctag=soup.select_one(CONTENT_SELECTOR)
    if not ttag or not ctag: return url
    raw_t = ttag.get_text()
    raw_c = ctag.get_text(separator=" ",strip=True).replace("\n","").replace("「",'"').replace("」",'"')
    t = normalize_text(raw_t,True,False)
    t = clean_title(t, TITLE_LIMIT)

    if not t.strip():  # 如果处理后的标题为空或全是空格
        t = raw_t
    t=sanitize_filename(t)

    c = normalize_text(raw_c,True,False)
    out=f"{t}\n{c}"
    path=os.path.join(OUTPUT_DIR,f"{t}.txt")
    if os.path.exists(path):
        old=open(path,'r',encoding='utf-8').read()
        if len(out)>=len(old):
            open(path,'w',encoding='utf-8').write(out)
    else:
        open(path,'w',encoding='utf-8').write(out)
    return None

async def main():
    page_sem = asyncio.Semaphore(SEM_LIMIT)
    post_sem = asyncio.Semaphore(SEM_LIMIT)
    async with httpx.AsyncClient(http2=True) as client:
        # 并发抓取页面链接
        pages = list(range(START_PAGE,END_PAGE+1))
        page_tasks = [asyncio.create_task(extract_links_page(page_sem,client,p)) for p in pages]
        all_links=[]
        for fut in tqdm(asyncio.as_completed(page_tasks), total=len(page_tasks), desc="页面检索进度"):
            links = await fut
            all_links.extend(links)
            await asyncio.sleep(SLEEP_SECONDS)

        # 并发抓取帖子内容
        failed = all_links
        for i in range(MAX_RETRY_ROUNDS):
            if not failed: break
            print(f"🔁 第 {i+1} 轮内容抓取，共 {len(failed)} 个链接")
            post_tasks = [asyncio.create_task(fetch_post_page(post_sem,client,url)) for url in failed]
            results=[]
            for fut in tqdm(asyncio.as_completed(post_tasks), total=len(post_tasks),
                            desc=f"内容抓取进度-第{i+1}轮"):
                res = await fut
                if res: results.append(res)
            failed = results

    if failed:
        with open(FAILED_LOG,"w",encoding="utf-8") as f:
            f.write("\n".join(failed))
        print(f"\n❌ 最终 {len(failed)} 条失败，已写入 {FAILED_LOG}")
    else:
        print("\n✅ 全部完成！")

if __name__=="__main__":
    asyncio.run(main())
