import os
from pathlib import Path
from urllib.parse import urlsplit

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
MANIFESTS_DIR = DATA_DIR / "manifests"
DEMO_DATASET_FILE = Path(
    os.getenv("SPHEREX_DEMO_MANIFEST", str(MANIFESTS_DIR / "demo_dataset.json"))
).resolve()
DEMO_CACHE_ONLY = os.getenv("SPHEREX_DEMO_CACHE_ONLY") == "1"
FIXTURES_DIR = DATA_DIR / "fixtures"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

# Server
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
LOCAL_CORS_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:3000,http://127.0.0.1:3000"
)


def parse_cors_origins(value: str | None) -> list[str]:
    """Parse explicit browser origins. An empty setting disables cross-origin access."""
    entries = dict.fromkeys(part.strip() for part in (LOCAL_CORS_ORIGINS if value is None else value).split(","))
    entries.pop("", None)
    for origin in entries:
        try:
            url = urlsplit(origin)
            valid = (
                url.scheme in ("http", "https")
                and url.hostname is not None
                and url.username is None
                and not any(marker in origin for marker in ("*", "?", "#"))
                and not any(character.isspace() for character in origin)
                and not url.path
                and not url.netloc.endswith(":")
                and (url.port is None or url.port > 0)
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("CORS_ORIGINS must list explicit HTTP(S) origins without paths, credentials, or wildcards")
    return list(entries)


CORS_ORIGINS = parse_cors_origins(os.getenv("CORS_ORIGINS"))

# IRSA Services
IRSA_SIA_BASE_URL = os.getenv("IRSA_SIA_BASE_URL", "https://irsa.ipac.caltech.edu/SIA")
IRSA_TAP_BASE_URL = os.getenv("IRSA_TAP_BASE_URL", "https://irsa.ipac.caltech.edu/TAP/sync")
IRSA_IBE_BASE_URL = os.getenv("IRSA_IBE_BASE_URL", "https://irsa.ipac.caltech.edu/ibe/data/spherex")

# Science & Search Defaults
DEFAULT_FOV_DEG = float(os.getenv("DEFAULT_FOV_DEG", "0.05"))
MAX_FOV_DEG = float(os.getenv("MAX_FOV_DEG", "0.3"))
DEFAULT_COLLECTION = os.getenv("DEFAULT_COLLECTION", "spherex_dr1")
# Explicit collection list for the multi-release search. Deployments can add
# a new IRSA collection without turning the query into an all-archive search.
SEARCH_COLLECTIONS = tuple(dict.fromkeys(
    item.strip() for item in os.getenv("SPHEREX_SEARCH_COLLECTIONS", "spherex_dr1,spherex_qr3").split(",")
    if item.strip() and item.strip().upper() != "ALL"
)) or ("spherex_dr1", "spherex_qr3")
DEFAULT_STRETCH = os.getenv("DEFAULT_STRETCH", "asinh")
