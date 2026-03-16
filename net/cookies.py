#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSL
# Copyright (c) 2026 Kan Liu. All rights reserved.

"""
Project: patest
File: net/cookies.py
Author: Kan Liu
Email: lkbhg@outlook.com
GitHub: https://github.com/lkbhg/
Created: 2026-03-16
License: BSL License
Description:
    cookies module for patest, including get_cookies and build_identity_pool.
"""



import requests
from requests.cookies import RequestsCookieJar
from bs4 import BeautifulSoup
from .header import get_random_headers
import random
from typing import Any


def get_cookies(url: str)->RequestsCookieJar | Any:

    session = requests.Session()

    headers = get_random_headers()

    # GET 页面（拿 tok）
    resp = session.get(url, headers=headers)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form", id="s18f")

    data = {}
    for inp in form.find_all("input"):  # type: ignore
        data[inp["name"]] = inp.get("value", "")

    # data == {'tok': '...', 'safe_agree': '1'}

    # POST 当前页面（等价 submitEnter）
    resp = session.post(
        url, data=data, headers={**headers, "Referer": url}, allow_redirects=True
    )

    # print("cookies:", session.cookies)

    resp = session.get(url=url, headers=headers, verify=True)  # verify=True 加密

    # print(resp.status_code)
    # print(resp.url)
    # print(resp.text[:300])

    if resp.status_code == 200:
        return session.cookies
    else:
        s:RequestsCookieJar



import httpx
from bs4 import BeautifulSoup
from .header import get_random_headers
import asyncio
from config import Identity
from typing import Dict

async def get_identity_async(
    url: str,
    form_id: str,
    sem: asyncio.Semaphore,
) -> Identity:
    headers = get_random_headers()

    async with sem:
        async with httpx.AsyncClient(
            headers=headers,
            follow_redirects=True,
            timeout=10.0,
        ) as client:

            # 1️⃣ GET 页面
            r = await client.get(url)
            r.raise_for_status()

            # 2️⃣ 解析 HTML（lxml）
            soup = BeautifulSoup(r.text, "lxml")
            form = soup.find("form", id=form_id)
            if not form:
                raise RuntimeError(f"form {form_id} not found")

            # 3️⃣ 构造 POST 数据（类型收敛点）
            data: Dict[str, str] = {}

            for inp in form.find_all("input"):
                name = inp.get("name")
                if not isinstance(name, str):
                    continue

                value = inp.get("value")

                if isinstance(value, list):
                    value = value[0]
                elif value is None:
                    value = ""

                data[name] = str(value)

            # 4️⃣ POST 提交表单
            await client.post(
                url,
                data=data,
                headers={**headers, "Referer": url},
            )

            # 5️⃣ 再次 GET，确认 cookies 生效
            r = await client.get(url)
            r.raise_for_status()

            return Identity(
                headers=headers,
                cookies=client.cookies,
            )



async def build_identity_pool(
    url: str,
    form_id: str,
    target_size: int,
    max_concurrency: int = 2,      # ⭐️ 同时最多几个 identity
    batch_size: int = 2,            # 每一轮创建几个
    min_delay: float = 1.0,         # 请求间最小延迟
    max_delay: float = 2.0,         # 请求间最大延迟
    max_rounds: int = 5,            # 最多尝试多少轮
) -> list[Identity]:

    identities: list[Identity] = []
    sem = asyncio.Semaphore(max_concurrency)

    round_no = 0
    while len(identities) < target_size and round_no < max_rounds:
        round_no += 1

        need = target_size - len(identities)
        current_batch = min(batch_size, need)

        tasks = [
            get_identity_async(url, form_id, sem)
            for _ in range(current_batch)
        ]

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True,  # ⭐️ 关键：永不抛异常
        )

        for r in results:
            if isinstance(r, Identity):
                identities.append(r)

        # ⭐️ 核心：像真人一样慢
        await asyncio.sleep(random.uniform(min_delay, max_delay))

    return identities

