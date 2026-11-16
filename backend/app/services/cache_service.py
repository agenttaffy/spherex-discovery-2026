import hashlib
from pathlib import Path
from typing import Optional
from app.config import CACHE_DIR, DEMO_CACHE_ONLY, DEMO_DATASET_FILE, MANIFESTS_DIR

class CacheService:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_key_path(self, key: str, extension: str = ".fits") -> Path:
        hashed = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{hashed}{extension}"

    def get(self, key: str) -> Optional[bytes]:
        path = self._get_key_path(key)
        candidates = [path]
        if self.cache_dir == CACHE_DIR and DEMO_DATASET_FILE.parent != MANIFESTS_DIR:
            candidates.append(DEMO_DATASET_FILE.parent / path.name)
        if self.cache_dir == CACHE_DIR:
            candidates.append(self.cache_dir / "demo-comparison" / path.name)
        for candidate in candidates:
            try:
                return candidate.read_bytes()
            except OSError:
                continue
        return None

    def get_verified(self, key: str, sha256: str) -> bytes | None:
        data = self.get(key)
        if data is not None and hashlib.sha256(data).hexdigest() == sha256:
            return data
        return None

    def set(self, key: str, data: bytes) -> Path:
        path = self._get_key_path(key)
        path.write_bytes(data)
        return path

    def count(self) -> int:
        return len(list(self.cache_dir.glob("*.fits")))

cache_service = CacheService()
