# translation-service

纯翻译服务：接收文本 → 查缓存 → 调 DeepL API → 返回翻译。

不负责 markdown 格式处理、术语表、映射表、后处理、文件遍历。
这些职责由调用方（sync-gitee-hub）承担。

## 架构

```
translation-service/
├── translator.py       # 纯翻译（translate 函数 + CLI）
├── cache_manager.py    # 缓存管理（段落级缓存 + API 使用量记录）
└── cache/
    ├── cache.json      # {sha256: {source, api_result, ts}}
    └── usage.json      # {total_chars, api_calls, cache_hits, monthly}
```

## 用法

### 模块（sync-gitee-hub 调用）

```python
from translator import translate
from cache_manager import CacheManager

cache_mgr = CacheManager('cache/').load()
result, from_cache = translate(text, api_key, cache_mgr)
cache_mgr.save()
```

### CLI

```bash
python translator.py --input <file> --cache-dir <dir> --api-key <key> [--force]
```
