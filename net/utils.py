#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: net/utils.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    utils module for patest, including helper functions for link extraction and page processing.
"""


import requests
import time
from bs4 import BeautifulSoup, Comment, Tag
from requests.cookies import RequestsCookieJar
from .header import get_keep_headers
from text import content, title
from pathlib import Path
import os
from config import Networks, Text


def extract_link_from_page(
    page_index: int, NETWORKS: Networks, cookie: RequestsCookieJar
) -> list[str]:
    last_exc: Exception | None = None

    url = (
        f"{NETWORKS.base_url}{NETWORKS.table_suffix}{NETWORKS.page_suffix}{page_index}"
    )

    for i in range(NETWORKS.retry_rounds):
        try:
            with requests.get(
                url, headers=get_keep_headers(), cookies=cookie, timeout=10
            ) as r:
                if r.status_code == 200:
                    return extract_links(page_index, r.text)
                    # return r.text
                else:
                    last_exc = RuntimeError(f"HTTP {r.status_code} for {url}")
        except requests.RequestException as e:
            last_exc = e

        time.sleep(0.1)

    # 重试耗尽，直接终止
    raise RuntimeError(
        f"Failed to fetch {url} after {NETWORKS.retry_rounds} retries"
    ) from last_exc


def extract_links(page_index: int, html: str) -> list[str]:

    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    trs = []
    if page_index == 1:
        ads = list(
            soup.find_all(string=lambda t: isinstance(t, Comment) and "广告连接" in t)
        )
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

    for tr in trs:
        a = tr.select_one("a.subject")
        if a and a.get("href"):
            href: str = a["href"].split("&")[0]  # type: ignore #temp delete
            links.append(href)

    return links


def extract_page(
    link: str, NETWORKS: Networks, cookie: RequestsCookieJar, TEXT: Text
) -> dict:

    url = f"{NETWORKS.base_url}{link}"

    with requests.get(url, headers=get_keep_headers(), cookies=cookie, timeout=10) as r:
        if r.status_code == 200:
            html = r.text
            if not html:
                return {"url": url, "error": True}
            soup = BeautifulSoup(html, "html.parser")
            ttag = soup.select_one(NETWORKS.title_selector)
            ctag = soup.select_one(NETWORKS.content_selector)
            if not ttag or not ctag:
                return {"url": url, "error": True}
            raw_t = ttag.get_text()

            # for br in ctag.find_all("br"):
            #     br.replace_with("\n")
            #     content = ctag.get_text(separator="\n", strip=true)

            raw_c = (
                ctag.get_text(separator="\n", strip=True)
                # .replace("\n", "")
                # .replace("「", '"')
                # .replace("」", '"')
            )
            t = content(raw_t)
            fname = title(t, TEXT)
            c = content(raw_c)

            # write_full_file(NETWORKS.output_dir, fname, c)

            return {"url": url, "filename": fname, "text": f"{fname}\n{c}"}
        else:
            return {"url": url, "error": f"HTTP {r.status_code}"}

        # time.sleep(0.1)


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
