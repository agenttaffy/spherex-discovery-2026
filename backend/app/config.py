import os
from pathlib import Path
from typing import List

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
MANIFESTS_DIR = DATA_DIR / "manifests"
FIXTURES_DIR = DATA_DIR / "fixtures"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

# Server
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
CORS_ORIGINS: List[str] = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000").split(",")
    if origin.strip()
]

# IRSA Services
IRSA_SIA_BASE_URL = os.getenv("IRSA_SIA_BASE_URL", "https://irsa.ipac.caltech.edu/SIA")
IRSA_TAP_BASE_URL = os.getenv("IRSA_TAP_BASE_URL", "https://irsa.ipac.caltech.edu/TAP/sync")
IRSA_IBE_BASE_URL = os.getenv("IRSA_IBE_BASE_URL", "https://irsa.ipac.caltech.edu/ibe/data/spherex")

# Science & Search Defaults
DEFAULT_FOV_DEG = float(os.getenv("DEFAULT_FOV_DEG", "0.05"))
MAX_FOV_DEG = float(os.getenv("MAX_FOV_DEG", "0.3"))
DEFAULT_COLLECTION = os.getenv("DEFAULT_COLLECTION", "spherex_dr1")
DEFAULT_STRETCH = os.getenv("DEFAULT_STRETCH", "asinh")
