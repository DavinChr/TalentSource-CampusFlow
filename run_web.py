#!/usr/bin/env python3
"""
CampusFlow — Web UI Runner
==========================
Jalankan perintah ini untuk memulai antarmuka Web CampusFlow:
    python run_web.py

Lalu buka peramban (browser) di:
    http://localhost:8000
"""

import os
import sys
import webbrowser
from pathlib import Path

# Pastikan direktori root berada dalam path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import uvicorn
from src.web import app

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    print("\n" + "=" * 65)
    print("🏛️  CampusFlow — Academic Facility & Event Coordinator")
    print(f"🌐 Web UI Server berjalan di: http://{host}:{port}")
    print("💡 Tekan Ctrl+C di terminal ini untuk mematikan server.")
    print("=" * 65 + "\n")

    # Buka browser secara otomatis hanya jika di lingkungan desktop lokal (bukan cloud container seperti Docker/Northflank/Render)
    if os.getenv("RENDER") is None and os.getenv("SPACE_ID") is None and os.getenv("NORTHFLANK") is None and os.getenv("KUBERNETES_SERVICE_HOST") is None:
        if sys.platform.startswith("win"):
            try:
                webbrowser.open(f"http://localhost:{port}")
            except Exception:
                pass

    uvicorn.run(app, host=host, port=port, log_level="info")
