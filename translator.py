#!/usr/bin/env python3
"""
翻译服务：缓存查询 + 调 DeepL API。
不负责：占位符保护、后处理、术语表、映射表、文件遍历。

用法（模块）:
  from translator import translate
  from cache_manager import CacheManager
  cache_mgr = CacheManager(cache_dir).load()
  result, from_cache = translate(text, api_key, cache_mgr, force=False)

用法（CLI）:
  python translator.py --input <file> --api-key <key>
"""
import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

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

    if resp.status_code == 456:
        msg = "DeepL API quota exceeded (HTTP 456). Monthly limit reached."
        print(f"::error::{msg}")
        raise Exception(msg)

    if resp.status_code != 200:
        msg = f"DeepL API HTTP {resp.status_code}: {resp.text[:200]}"
        print(f"::error::{msg}")
        raise Exception(msg)

    result = resp.json()
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


def _translate_raw(text, api_key):
    """纯翻译：切分超长文本 → 调 API → 返回 (translated_text, used_chars)"""
    if not text.strip():
        return text, 0

    chunks = _split_by_length(text)
    parts = []
    total_used = 0
    for chunk in chunks:
        translated, used = call_deepl_api(chunk, api_key)
        parts.append(translated)
        total_used += used
        time.sleep(API_INTERVAL)

    return ''.join(parts), total_used


def translate(text, api_key, cache_mgr, force=False):
    """
    查缓存 → 命中返回 → 未命中调 API → 更新缓存
    返回 (translated_text, from_cache)
    """
    key = hashlib.sha256(text.encode('utf-8')).hexdigest()
    if not force:
        cached = cache_mgr.get(key)
        if cached is not None:
            return cached, True
    try:
        result, _used = _translate_raw(text, api_key)
    except Exception as e:
        if '456' in str(e) or 'quota' in str(e).lower():
            print("::error::DeepL API 额度已耗尽（HTTP 456）。缓存命中的段落仍正常使用，未命中段落保留原文。")
            print("::notice::请等待下月额度恢复后重新触发 workflow。")
        raise
    cache_mgr.set(key, text, result)
    return result, False


def main():
    parser = argparse.ArgumentParser(description='Translation service (cache + DeepL API)')
    parser.add_argument('--input', required=True, help='输入文件路径')
    parser.add_argument('--output', help='输出文件路径（默认覆盖输入）')
    parser.add_argument('--api-key', default=os.environ.get('DEEPL_API_KEY'))
    args = parser.parse_args()

    text = Path(args.input).read_text(encoding='utf-8')
    translated, _used = _translate_raw(text, args.api_key)

    out = args.output or args.input
    Path(out).write_text(translated, encoding='utf-8')
    print(f"Done: {_used} chars translated.")


if __name__ == '__main__':
    main()
