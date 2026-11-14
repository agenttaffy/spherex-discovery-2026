#!/usr/bin/env python3
"""
scripts/verify_environment.py
Verifies development environment: Python version, Node, npm, Git, critical packages, and IRSA connectivity.
"""
import sys
import subprocess
import shutil
import ssl
import certifi
import urllib.request
import json
from datetime import datetime

def check_command(cmd, name):
    path = shutil.which(cmd)
    if path:
        try:
            res = subprocess.run([cmd, "--version"], capture_output=True, text=True, check=True, shell=(sys.platform == "win32"))
            ver = res.stdout.strip().split("\n")[0]
            print(f"[OK] {name}: {ver} ({path})")
            return True, ver
        except Exception as e:
            print(f"[WARN] {name} found at {path} but failed --version: {e}")
            return True, "Unknown"
    else:
        print(f"[FAIL] {name} ({cmd}) not found in PATH")
        return False, None

def check_python_packages():
    required = ["fastapi", "uvicorn", "httpx", "astropy", "numpy", "scipy", "PIL", "pytest", "certifi"]
    all_ok = True
    for pkg in required:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "installed")
            print(f"[OK] Python package '{pkg}': {ver}")
        except ImportError:
            print(f"[FAIL] Missing Python package: {pkg}")
            all_ok = False
    return all_ok

def check_irsa_connectivity():
    url = "https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=circle+127.69444+-39.17760+0.01&RESPONSEFORMAT=CSV"
    print(f"\nTesting IRSA SIA connectivity to: {url[:60]}...")
    try:
        ctx = ssl.create_default_context(cafile=certifi.where())
        req = urllib.request.Request(url, headers={"User-Agent": "SPHEREx-Discovery-Verifier/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = resp.read(500).decode("utf-8", errors="ignore")
            if resp.status == 200 and "s_ra" in data:
                print(f"[OK] IRSA SIA endpoint reachable and returned valid CSV data (status {resp.status})")
                return True
            else:
                print(f"[FAIL] IRSA SIA unexpected response: status {resp.status}, preview: {data[:100]}")
                return False
    except Exception as e:
        print(f"[FAIL] IRSA SIA connection error: {e}")
        return False

def main():
    print("=" * 60)
    print("SPHEREx Discovery Environment Verification")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print("=" * 60)
    
    print("\n--- System Tools ---")
    py_ok, _ = check_command("python", "Python")
    node_ok, _ = check_command("node", "Node.js")
    npm_ok, _ = check_command("npm", "npm")
    git_ok, _ = check_command("git", "Git")
    
    print("\n--- Python Dependencies ---")
    pkg_ok = check_python_packages()
    
    print("\n--- NASA/IPAC Connectivity ---")
    irsa_ok = check_irsa_connectivity()
    
    all_pass = py_ok and node_ok and npm_ok and git_ok and pkg_ok and irsa_ok
    print("\n" + "=" * 60)
    if all_pass:
        print("[SUCCESS] All environment requirements passed!")
    else:
        print("[WARN] Some checks failed or are incomplete.")
    print("=" * 60)
    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
