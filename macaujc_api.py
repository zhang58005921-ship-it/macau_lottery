#!/usr/bin/env python3
"""macaujc.com REST API - 直接调用官方接口，零第三方依赖"""

import json
import ssl
import urllib.request


# 创建忽略证书验证的 context（一次性，避免重复创建）
_ctxt = None

def _ssl_context():
    global _ctxt
    if _ctxt is None:
        _ctxt = ssl.create_default_context()
        _ctxt.check_hostname = False
        _ctxt.verify_mode = ssl.CERT_NONE
    return _ctxt


API_BASE = "https://macaumarksix.com/api"
HISTORY_BASE = "https://history.macaumarksix.com/history/macaujc2"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _get(url, timeout=15):
    """通用 GET 请求，自动处理 SSL 和重试"""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last_err = None
    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=timeout, context=_ssl_context())
            return json.loads(resp.read())
        except Exception as e:
            last_err = e
    raise last_err


def get_latest():
    """获取最新一期开奖结果"""
    try:
        data = _get(f"{API_BASE}/macaujc2.com")
        if isinstance(data, list):
            return data[0] if data else None
        return (data.get("data", [None]) or [None])[0]
    except Exception as e:
        print(f"get_latest failed: {e}")
        return None


def get_history(year):
    """获取指定年份历史数据，返回 list[dict]"""
    try:
        data = _get(f"{HISTORY_BASE}/y/{year}")
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and data.get("code") == 200:
            return data.get("data", [])
        return []
    except Exception as e:
        print(f"get_history({year}) failed: {e}")
        return []


def fetch_all(years=None):
    """批量获取多年数据"""
    if years is None:
        years = [2023, 2024, 2025, 2026]
    all_data = []
    for y in years:
        data = get_history(y)
        if data:
            all_data.extend(data)
            print(f"  {y}: {len(data)} records")
    return all_data