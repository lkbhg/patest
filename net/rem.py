#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: net/rem.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    rem module for patest, including booster.
"""



import asyncio
from tqdm import tqdm
import random
import httpx
from httpx import Cookies
from bs4 import BeautifulSoup, Comment, Tag
from .header import get_keep_headers
from text import content, title
from pathlib import Path
import os
from config import Networks, Text
from .cookies import build_identity_pool
from .writer import AsyncFileWriter, WriteMode, WriteTask


async def extract_link_from_page(
    page_index: int,
    NETWORKS: Networks,
    cookie: Cookies,
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
) -> list[str]:
    last_exc: Exception | None = None

    url = (
        f"{NETWORKS.base_url}{NETWORKS.table_suffix}{NETWORKS.page_suffix}{page_index}"
    )

    for _ in range(NETWORKS.retry_rounds):
        try:
            async with sem:  # ⭐️ 限并发
                r = await client.get(
                    url,
                    headers=get_keep_headers(),
                    cookies=cookie,
                    timeout=10,
                )

            if r.status_code == 200:
                return extract_links(page_index, r.text)
            else:
                last_exc = RuntimeError(f"HTTP {r.status_code} for {url}")

        except httpx.RequestError as e:
            last_exc = e

        await asyncio.sleep(0.1)

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


async def extract_page(
    link: str,
    NETWORKS: Networks,
    cookie: Cookies,
    TEXT: Text,
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
) -> dict:

    url = f"{NETWORKS.base_url}{link}"

    try:
        async with sem:  # ⭐️ 限并发
            r = await client.get(
                url,
                headers=get_keep_headers(),
                cookies=cookie,
                timeout=10,
            )
    except httpx.RequestError as e:
        return {"url": url, "error": str(e)}

    if r.status_code != 200:
        return {"url": url, "error": f"HTTP {r.status_code}"}

    html = r.text
    if not html:
        return {"url": url, "error": True}

    soup = BeautifulSoup(html, "html.parser")
    ttag = soup.select_one(NETWORKS.title_selector)
    ctag = soup.select_one(NETWORKS.content_selector)
    if not ttag or not ctag:
        return {"url": url, "error": True}

    raw_t = ttag.get_text()
    raw_c = ctag.get_text(separator="\n", strip=True)

    t = content(raw_t)
    fname = title(t, TEXT)
    c = content(raw_c)

    return {"url": url, "filename": fname, "text": f"{fname}\n{c}"}


async def sem_threads(NETWORKS: Networks, TEXT: Text):
    links_list: list[list[str]] = []

    writer = AsyncFileWriter(fsync=False)  # 🔥 默认关 fsync
    await writer.start()

    # ===== 1️⃣ Identity pool =====
    identity_pool = await build_identity_pool(
        NETWORKS.base_url, NETWORKS.push_cookie_id, NETWORKS.identity_pool_size
    )

    # 分离 semaphore（值可以相同）
    page_sem = asyncio.Semaphore(NETWORKS.sem_threads)
    post_sem = asyncio.Semaphore(NETWORKS.sem_threads)

    # ===== 2️⃣ 复用一个 AsyncClient =====
    async with httpx.AsyncClient(
        http2=True,
        timeout=10,
    ) as client:

        # ========= 分页抓取 =========
        page_tasks = [
            extract_link_from_page(
                page_index=p,
                NETWORKS=NETWORKS,
                cookie=(identity := random.choice(identity_pool)).cookies,
                client=client,
                sem=page_sem,
            )
            for p in range(NETWORKS.start_page, NETWORKS.end_page + 1)
        ]

        for coro in tqdm(
            asyncio.as_completed(page_tasks),
            total=len(page_tasks),
            desc="抓取分页,并发提取链接",
            unit="page",
            ncols=150,
        ):
            try:
                links = await coro
                links_list.append(links)
            except Exception as e:
                print(f"Page-get failed: {e}")

        all_links = [link for page in links_list for link in page]
        del links_list

        # ========= 内容抓取（带 retry） =========
        failed: list[str] = all_links

        for rnd in range(NETWORKS.retry_rounds):
            if not failed:
                break

            await asyncio.sleep(15)
            print(f"🔁 第 {rnd + 1} 轮内容抓取，共 {len(failed)} 条")

            tasks = [
                extract_page(
                    link=url,
                    NETWORKS=NETWORKS,
                    cookie=(identity := random.choice(identity_pool)).cookies,
                    TEXT=TEXT,
                    client=client,
                    sem=post_sem,
                )
                for url in failed
            ]

            failed = []

            for coro in tqdm(
                asyncio.as_completed(tasks),
                total=len(tasks),
                desc=f"下载 R{rnd + 1}",
                ncols=150,
            ):
                try:
                    res = await coro
                    if res.get("error"):
                        failed.append(res["url"])
                    else:
                        writer.submit_nowait(
                            WriteTask(
                                output_dir=NETWORKS.output_dir,
                                filename=res["filename"],
                                content=res["text"],
                                mode=WriteMode.OVERWRITE_IF_LARGER,
                            )
                        )
                except Exception:
                    failed.append(res["url"])

    await writer.stop()

    # ========= 失败记录 =========
    if failed:
        with open(NETWORKS.failed_log, "w", encoding="utf-8") as f:
            f.write("\n".join(failed))
        print(f"\n❌ {len(failed)} 条失败，已写入 {NETWORKS.failed_log}")
    else:
        print(f"\n✅ {len(all_links)} 条全部完成！")


def booster(NETWORKS: Networks, TEXT: Text):
    asyncio.run(sem_threads(NETWORKS, TEXT))
