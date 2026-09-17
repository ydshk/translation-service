#!/usr/bin/env python3
"""
翻译服务：纯翻译，不含 markdown 格式处理。

职责：接收纯文本 → 查缓存 → 调 DeepL API → 返回翻译
不负责：占位符保护、后处理、术语表、映射表、文件遍历

用法（模块）:
  from translator import translate
  result, from_cache = translate(text, api_key, cache_mgr)

用法（CLI）:
  python translator.py --input <file> --cache-dir <dir> --api-key <key>
"""
import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

from cache_manager import CacheManager

MAX_CHUNK_BYTES = 4000
API_INTERVAL = 0.25


def call_deepl_api(text, api_key):
    """调用 DeepL API，返回 (translated_text, used_chars)"""
    import requests

    if not api_key:
        raise Exception("DeepL API Key is empty.")

    endpoint = "https://api-free.deepl.com/v2/translate" if api_key.endswith(':fx') else "https://api.deepl.com/v2/translate"

    resp = requests.post(
        endpoint,
        data={"text": text, "source_lang": "EN", "target_lang": "ZH"},
        headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
        timeout=30,
    )

    if resp.status_code != 200:
        raise Exception(f"DeepL API HTTP {resp.status_code}: {resp.text[:200]}")

    result = resp.json()
    if "message" in result:
        raise Exception(f"DeepL API error: {result['message']}")
    if "translations" not in result or not result["translations"]:
        raise Exception(f"Unexpected response: {result}")

    return result["translations"][0]["text"], len(text)


def _split_by_length(text):
    """超长文本按字节长度切分"""
    if len(text.encode('utf-8')) <= MAX_CHUNK_BYTES:
        return [text]
    chunks = []
    for j in range(0, len(text), MAX_CHUNK_BYTES):
        chunk_str = text[j:j + MAX_CHUNK_BYTES]
        if chunk_str:
            chunks.append(chunk_str)
    return chunks


def translate(text, api_key, cache_mgr, force=False):
    """
    翻译纯文本：查缓存 → 调 API → 返回翻译
    返回 (translated_text, from_cache)
    """
    if not text.strip():
        return text, True

    cache_key = hashlib.sha256(text.encode()).hexdigest()
    cached = cache_mgr.get(cache_key) if not force else None

    if cached is not None:
        return cached, True

    sub_chunks = _split_by_length(text)
    parts = []
    for sc in sub_chunks:
        translated, used = call_deepl_api(sc, api_key)
        parts.append(translated)
        cache_mgr.record_api_call(used)
        time.sleep(API_INTERVAL)

    result = ''.join(parts)
    cache_mgr.set(cache_key, text, result)
    return result, False


def main():
    parser = argparse.ArgumentParser(description='Pure translation service')
    parser.add_argument('--input', required=True, help='输入文件路径')
    parser.add_argument('--output', help='输出文件路径（默认覆盖输入）')
    parser.add_argument('--cache-dir', required=True, help='缓存目录')
    parser.add_argument('--api-key', default=os.environ.get('DEEPL_API_KEY'))
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()

    cache_mgr = CacheManager(args.cache_dir).load()
    text = Path(args.input).read_text(encoding='utf-8')
    translated, from_cache = translate(text, args.api_key, cache_mgr, args.force)

    out = args.output or args.input
    Path(out).write_text(translated, encoding='utf-8')
    cache_mgr.save()

    print(f"Done: {'cache hit' if from_cache else 'API call'}, stats: {cache_mgr.stats()}")


if __name__ == '__main__':
    main()
