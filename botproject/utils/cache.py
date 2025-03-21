from typing import Dict, Any, Optional
import time
from config import CACHE_MAX_SIZE

class Cache:
    def __init__(self, max_size: int = CACHE_MAX_SIZE):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None

        item = self.cache[key]
        if item['expires'] < time.time():
            del self.cache[key]
            return None

        return item['value']

    def set(self, key: str, value: Any, timeout: int = 300) -> None:
        self.cache[key] = {
            'value': value,
            'expires': time.time() + timeout
        }

        if len(self.cache) > self.max_size:
            self.cleanup(force=True)

    def delete(self, key: str) -> None:
        if key in self.cache:
            del self.cache[key]

    def cleanup(self, force: bool = False) -> None:
        now = time.time()
        expired_keys = [k for k, v in self.cache.items() if v['expires'] < now]

        for key in expired_keys:
            del self.cache[key]

        if force and len(self.cache) > self.max_size:
            sorted_items = sorted(
                self.cache.items(),
                key=lambda x: x[1]['expires']
            )

            items_to_remove = int(len(sorted_items) * 0.25)
            for key, _ in sorted_items[:items_to_remove]:
                del self.cache[key]

cache = Cache()

