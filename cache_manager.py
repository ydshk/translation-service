"""
缓存管理：段落级翻译缓存 + API 使用量记录。

缓存结构 cache.json:
  {sha256: {source: "英文段落(截断200)", api_result: "DeepL返回", ts: "ISO时间"}}

使用量 usage.json:
  {total_chars: 累计API字符, api_calls: API调用次数, cache_hits: 缓存命中次数, monthly: {2026-09: {chars, calls}}}
"""
import json
from datetime import datetime, timezone
from pathlib import Path


class CacheManager:
    def __init__(self, cache_dir):
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / 'cache.json'
        self.usage_file = self.cache_dir / 'usage.json'
        self.cache = {}
        self.usage = {'total_chars': 0, 'api_calls': 0, 'cache_hits': 0, 'monthly': {}}
        self._dirty = False

    def load(self):
        if self.cache_file.exists():
            self.cache = json.loads(self.cache_file.read_text(encoding='utf-8'))
        if self.usage_file.exists():
            self.usage = json.loads(self.usage_file.read_text(encoding='utf-8'))
            self.usage.setdefault('monthly', {})
        return self

    def get(self, key):
        """查缓存，命中返回 api_result，未命中返回 None"""
        entry = self.cache.get(key)
        if entry is not None:
            self.usage['cache_hits'] += 1
            return entry['api_result']
        return None

    def set(self, key, source, api_result):
        """写缓存"""
        self.cache[key] = {
            'source': source[:200],
            'api_result': api_result,
            'ts': datetime.now(timezone.utc).isoformat(),
        }
        self._dirty = True

    def record_api_call(self, chars):
        """记录一次 API 调用消耗"""
        self.usage['total_chars'] += chars
        self.usage['api_calls'] += 1
        month = datetime.now(timezone.utc).strftime('%Y-%m')
        m = self.usage['monthly'].setdefault(month, {'chars': 0, 'calls': 0})
        m['chars'] += chars
        m['calls'] += 1
        self._dirty = True

    def stats(self):
        return {
            'cache_entries': len(self.cache),
            'total_chars': self.usage['total_chars'],
            'api_calls': self.usage['api_calls'],
            'cache_hits': self.usage['cache_hits'],
        }

    def save(self):
        """保存缓存和使用量到文件"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding='utf-8')
        self.usage_file.write_text(json.dumps(self.usage, ensure_ascii=False, indent=2), encoding='utf-8')