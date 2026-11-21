# -*- coding: utf-8 -*-
"""کش درون‌پردازشی پاسخ‌های GET برای افزایش سرعت داشبوردها.

- کلید کش = نسخه داده + مسیر کامل + query string
- با هر تغییر داده (import / reset-db / recompute) نسخه داده بامپ می‌شود
- TTL محافظتی کوتاه فقط حکم شبکه امن دارد
"""
import functools
import time

from flask import request

_CACHE = {}
_CACHE_TIMES = {}
_TTL = 120          # ثانیه — فقط شبکهٔ امن؛ با bump داده‌ها فوراً بی‌اعتبار می‌شوند
_GEN = 1            # نسخه داده؛ با هر تغییر داده افزایش می‌یابد
MAX_ENTRIES = 256


def bump():
    """با هر تغییر داده فراخوانی شود تا کل کش بی‌اعتبار گردد."""
    global _GEN
    _GEN += 1
    _CACHE.clear()
    _CACHE_TIMES.clear()


def cached(ttl=_TTL):
    """دکوراتور مسیرهای GET؛ پاسخ jsonify کامل را کش می‌کند."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if request.method != 'GET':
                return fn(*args, **kwargs)
            key = f'{_GEN}|{request.full_path}'
            now = time.time()
            hit = _CACHE.get(key)
            if hit is not None and now - _CACHE_TIMES.get(key, 0) < ttl:
                return hit
            resp = fn(*args, **kwargs)
            try:
                if len(_CACHE) >= MAX_ENTRIES:
                    _CACHE.clear()
                    _CACHE_TIMES.clear()
                _CACHE[key] = resp
                _CACHE_TIMES[key] = now
            except Exception:  # noqa
                pass
            return resp
        return wrapper
    return deco
