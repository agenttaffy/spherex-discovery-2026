import hashlib
from pathlib import Path
from typing import Optional
from app.config import CACHE_DIR

class CacheService:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_key_path(self, key: str, extension: str = ".fits") -> Path:
        hashed = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{hashed}{extension}"

    def get(self, key: str) -> Optional[bytes]:
        path = self._get_key_path(key)
        if path.exists():
            try:
                return path.read_bytes()
            except Exception:
                return None
        return None

    def set(self, key: str, data: bytes) -> Path:
        path = self._get_key_path(key)
        path.write_bytes(data)
        return path

    def count(self) -> int:
        return len(list(self.cache_dir.glob("*.fits")))

cache_service = CacheService()
