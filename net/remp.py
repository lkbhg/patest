#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: net/remp.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    remp module for patest, including remp functionality.
"""


import asyncio
from tqdm import tqdm
import random
import httpx
import h2.exceptions
from lxml import etree
from bs4 import BeautifulSoup, Comment, Tag
from text import content, title
from config import Networks, Text, Identity
from .cookies import build_identity_pool
from .writer import write_full_file
from typing import Any
import multiprocessing as mp
import math
import time


async def extract_link_from_page(
    page_index: int,
    NETWORKS: Networks,
    identity: Identity,
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
                    headers=identity.headers,
                    cookies=identity.cookies,
                    timeout=NETWORKS.timeout,
                )

            if r.status_code == 200:
                return extract_links_lxml(page_index, r.text)
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

def extract_links_lxml(page_index: int, html: str) -> list[str]:
    if not html:
        return []

    links: list[str] = []

    parser = etree.HTMLParser()
    root = etree.HTML(html, parser)

    trs = []

    if page_index == 1:
        # 找到注释节点，类似 BeautifulSoup Comment
        comments = root.xpath("//comment()")
        ads = [c for c in comments if "广告连接" in c.text]
        if len(ads) >= 2:
            start_comment, end_comment = ads[0], ads[1]
            found_start = False
            for el in root.iter():
                if el is start_comment:
                    found_start = True
                    continue
                if el is end_comment:
                    break
                if found_start and el.tag == "tr":
                    cls = el.get("class") or ""
                    if "tr3" in cls and "t_one" in cls:
                        trs.append(el)
    else:
        # 普通页直接选 tr.tr3.t_one
        trs = root.xpath("//tr[contains(@class,'tr3') and contains(@class,'t_one')]")

    # 提取 <a class="subject"> 的 href
    for tr in trs:
        a = tr.xpath(".//a[@class='subject']/@href")
        if a:
            href: str = a[0].split("&")[0]
            links.append(href)

    return links

async def extract_page(
    link: str,
    NETWORKS: Networks,
    identity: Identity,
    TEXT: Text,
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
) -> dict:

    url = f"{NETWORKS.base_url}{link}"

    try:
        async with sem:  # ⭐️ 限并发
            r = await client.get(
                url,
                headers=identity.headers,
                cookies=identity.cookies,
                timeout=NETWORKS.timeout,
            )
    except (
        httpx.RequestError,
        RuntimeError,                 # client closed / loop state
        asyncio.TimeoutError,
        h2.exceptions.ProtocolError,
    ) as e:
        return {
            "url": link,
            "error": f"{type(e).__name__}: {e}"
        }


    if r.status_code != 200:
        return {"url": link, "error": f"HTTP {r.status_code}"}

    html = r.text
    if not html:
        return {"url": link, "error": True}

    soup = BeautifulSoup(html, "html.parser")
    ttag = soup.select_one(NETWORKS.title_selector)
    ctag = soup.select_one(NETWORKS.content_selector)
    if not ttag or not ctag:
        return {"url": link, "error": True}

    raw_t = ttag.get_text()
    raw_c = ctag.get_text(separator="\n", strip=True)

    t = content(raw_t)
    fname = title(t, TEXT)
    c = content(raw_c)

    return {"url": link, "filename": fname, "text": f"{fname}\n{c}"}

async def fetch_all_links(NETWORKS: Networks) -> list[str]:
    """
    单进程 async 分页抓取
    返回所有正文链接，以及 identity pool
    """

    # ===== identity pool =====
    identity_pool = await build_identity_pool(
        NETWORKS.base_url,
        NETWORKS.push_cookie_id,
        NETWORKS.identity_pool_size
    )

    page_sem = asyncio.Semaphore(NETWORKS.sem_threads)
    links_list: list[list[str]] = []

    async with httpx.AsyncClient(http2=True, timeout=30) as client:

        page_tasks = [
            extract_link_from_page(
                page_index=p,
                NETWORKS=NETWORKS,
                identity=random.choice(identity_pool),
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
    return all_links

async def page_worker_main(
    worker_id: int,
    pages: list[int],
    NETWORKS: Networks,
    result_queue: Any,   # multiprocessing.Manager().list()
):
    identity_pool = await build_identity_pool(
        NETWORKS.base_url,
        NETWORKS.push_cookie_id,
        NETWORKS.identity_pool_size,
    )

    sem = asyncio.Semaphore(NETWORKS.sem_threads)
    local_links: list[str] = []

    async with httpx.AsyncClient(http2=True, timeout=NETWORKS.timeout) as client:
        tasks = [
            extract_link_from_page(
                page_index=p,
                NETWORKS=NETWORKS,
                identity=random.choice(identity_pool),
                client=client,
                sem=sem,
            )
            for p in pages
        ]

        for coro in asyncio.as_completed(tasks):
            try:
                links = await coro
                local_links.extend(links)
            except Exception as e:
                print(f"[PageWorker {worker_id}] failed: {e}")

    # ⚠️ 一次性写回，避免频繁 IPC
    result_queue.extend(local_links)

def run_page_worker(worker_id: int, pages: list[int], NETWORKS: Networks, result_queue: Any):
    asyncio.run(page_worker_main(worker_id, pages, NETWORKS, result_queue))

def chunkify_int(lst: list[int], n: int) -> list[list[int]]:
    size = math.ceil(len(lst) / n)
    return [lst[i:i+size] for i in range(0, len(lst), size)]

def fetch_all_links_multiprocess(NETWORKS: Networks) -> list[str]:
    pages = list(range(NETWORKS.start_page, NETWORKS.end_page + 1))

    cpu_cnt = min(mp.cpu_count(), 4)  # 分页不要太多进程
    chunks = chunkify_int(pages, cpu_cnt)

    manager = mp.Manager()
    result_links = manager.list()

    procs = []
    for i, chunk in enumerate(chunks):
        p = mp.Process(
            target=run_page_worker,
            args=(i, chunk, NETWORKS, result_links),
        )
        p.start()
        procs.append(p)

    with tqdm(
        total=len(pages),
        desc="抓取分页（多进程并发）",
        unit="page",
        ncols=150,
    ) as pbar:
        last = 0
        while any(p.is_alive() for p in procs):
            current = len(result_links)
            pbar.update(current - last)
            last = current
            time.sleep(0.2)

        # 最后补一次
        current = len(result_links)
        pbar.update(current - last)

    for p in procs:
        p.join()

    return list(result_links)


# ------------------ worker_main ------------------
async def worker_main(
    worker_id: int,
    links: list[str],
    NETWORKS:Networks,
    TEXT:Text,
    counter: Any,
    failed_global: Any,  # 共享 Manager.list()，记录失败
):
    """
    每个 worker 内独立生成 identity pool，并抓取正文
    更新共享 counter 供主进程 tqdm 显示
    """
    identity_pool = await build_identity_pool(
        NETWORKS.base_url,
        NETWORKS.push_cookie_id,
        NETWORKS.identity_pool_size
    )

    sem = asyncio.Semaphore(NETWORKS.sem_threads)
    failed_local: list[str] = links.copy()  # 每轮重试用

    async with httpx.AsyncClient(http2=True, timeout=NETWORKS.timeout) as client:
        for rnd in range(NETWORKS.retry_rounds):
            if not failed_local:
                break

            # print(f"[Worker {worker_id}] Round {rnd+1}, {len(failed_local)} items")

            tasks = [
                extract_page(
                    link=url,
                    NETWORKS=NETWORKS,
                    identity=random.choice(identity_pool),
                    TEXT=TEXT,
                    client=client,
                    sem=sem,
                )
                for url in failed_local
            ]

            failed_local = []
            for coro in asyncio.as_completed(tasks):
                res = await coro
                if res.get("error"):
                    failed_local.append(res["url"])
                else:
                    write_full_file(
                        NETWORKS.output_dir,
                        res["filename"],
                        res["text"],
                    )
                # 更新全局进度
                try:
                    with counter.get_lock():  # type: ignore
                        counter.value += 1
                except AttributeError:
                    counter.value += 1

        # worker 完成后把剩余失败链接加入全局共享列表
        failed_global.extend(failed_local)

# ------------------ run_worker ------------------
def run_worker(worker_id:int, links:list[str], NETWORKS:Networks, TEXT:Text, counter: Any, failed_global: Any):
    asyncio.run(worker_main(worker_id, links, NETWORKS, TEXT, counter, failed_global))


def chunkify(lst: list[str], n: int) -> list[list[str]]:
    size = math.ceil(len(lst) / n)
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def remp(NETWORKS: Networks, TEXT: Text):
    # # ===== 1️⃣ 先抓分页（单进程 async 就够）=====
    # all_links = asyncio.run(fetch_all_links(NETWORKS))

    all_links = fetch_all_links_multiprocess(NETWORKS)


    cpu_cnt = min(mp.cpu_count(),NETWORKS.process)
    chunks = chunkify(all_links, cpu_cnt)

    manager = mp.Manager()
    counter = manager.Value("i", 0)  # 全局进度计数
    failed_global = manager.list()  # 全局失败列表

    total = len(all_links)
    # print(f"Spawn {len(chunks)} workers to process {total} links")

    # 启动 worker
    procs = []
    for i, chunk in enumerate(chunks):
        p = mp.Process(
            target=run_worker,
            args=(i, chunk, NETWORKS, TEXT, counter, failed_global),
        )
        p.start()
        procs.append(p)

    # 主进程显示 tqdm
    with tqdm(total=total, desc="抓取正文", ncols=150, unit="item") as pbar:
        last = 0
        while any(p.is_alive() for p in procs):
            try:
                with counter.get_lock():  # type: ignore
                    current = counter.value
            except AttributeError:
                current = counter.value
            pbar.update(current - last)
            last = current


            time.sleep(0.1)

        # 最后更新一次
        try:
            with counter.get_lock():  # type: ignore
                current = counter.value
        except AttributeError:
            current = counter.value
        pbar.update(current - last)

    # 等待所有 worker 完成
    for p in procs:
        p.join()

    # ========= 写失败日志 =========
    failed_list = list(failed_global)
    if failed_list:
        with open(NETWORKS.failed_log, "w", encoding="utf-8") as f:
            f.write("\n".join(failed_list))
        print(f"\n❌ {len(failed_list)} 条失败，已写入 {NETWORKS.failed_log}")
    else:
        print(f"\n✅ {total} 条全部完成！")
