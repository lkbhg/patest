#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: net/core.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    core module for patest, including downloader, booster and remp.
"""


from tqdm import tqdm

from concurrent.futures import ThreadPoolExecutor, as_completed
from .utils import *
from .cookies import get_cookies
from config import Networks, Text


def downloader(NETWORKS: Networks, TEXT: Text):
    links_list: list[list[str]] = []

    cookie = get_cookies(NETWORKS.base_url)

    #cookie=RequestsCookieJar()

    # 使用线程池并发抓取
    with ThreadPoolExecutor(max_workers=NETWORKS.threads) as executor:
        futures = [
            executor.submit(
                extract_link_from_page,
                page_index,
                NETWORKS,  # 每个分页的 URL  # 重试次数
                cookie,
            )
            for page_index in range(
                NETWORKS.start_page, NETWORKS.end_page + 1
            )  # 为每个分页 URL 提交一个任务
        ]

        # 3. 等待任务完成，同时显示进度条
        for future in tqdm(
            as_completed(futures),
            total=NETWORKS.start_page - NETWORKS.end_page + 1,
            desc="抓取分页,并发提取链接",
            unit="page",
            ncols=150,
        ):
            try:
                links = future.result()  # 每页的链接列表
                links_list.append(links)  # append 成二维列表
            except Exception as e:
                print(f"Page-get failed: {e}")

    # 假设 links 是所有要处理的链接列表
    all_links = [link for page in links_list for link in page]
    del links_list

    # 并发下载解析并写文件
    failed = []

    for rnd in range(NETWORKS.retry_rounds):
        time.sleep(15)
        to_do = all_links if rnd == 0 else failed
        if not to_do:
            break
        failed = []

        with ThreadPoolExecutor(max_workers=NETWORKS.threads) as executor:
            future_to_url = {
                executor.submit(extract_page, url, NETWORKS, cookie, TEXT): url
                for url in to_do
            }

            for future in tqdm(
                as_completed(future_to_url),
                total=len(to_do),
                desc=f"下载 R{rnd+1}",
                ncols=150,
            ):
                # pass
                url = future_to_url[future]
                try:
                    res = future.result()
                    if res.get("error"):
                        failed.append(res["url"])
                    else:
                        write_full_file(NETWORKS.output_dir, res["filename"], res["text"])
                except Exception as e:
                    # 捕获线程内的异常，也算作失败
                    failed.append(url)

    # 记录失败 debug
    if failed:
        with open(NETWORKS.failed_log, "w", encoding="utf-8") as f:
            f.write("\n".join(failed))
        print(f"\n❌ {len(failed)} 条失败，已写入 {NETWORKS.failed_log}")
    else:
        print(f"\n✅ {len(all_links)} 条全部完成！")

