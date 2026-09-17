"""
段落级翻译缓存。

缓存结构 cache.json:
  {sha256: {source: "英文段落(截断200)", api_result: "DeepL返回", ts: "ISO时间"}}
"""
import json
from datetime import datetime, timezone
from pathlib import Path


class CacheManager:
    def __init__(self, cache_dir):
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / 'cache.json'
        self.cache = {}
        self._dirty = False

    def load(self):
        if self.cache_file.exists():
            self.cache = json.loads(self.cache_file.read_text(encoding='utf-8'))
        return self

    def get(self, key):
        """查缓存，命中返回 api_result，未命中返回 None"""
        entry = self.cache.get(key)
        if entry is not None:
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

    def stats(self):
        return {'cache_entries': len(self.cache)}

    def save(self):
        """保存缓存到文件"""
        if not self._dirty:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding='utf-8')
