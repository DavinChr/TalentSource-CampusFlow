#!/usr/bin/env python3
"""
CampusFlow — Web UI Runner
==========================
Jalankan perintah ini untuk memulai antarmuka Web CampusFlow:
    python run_web.py

Lalu buka peramban (browser) di:
    http://localhost:8000
"""

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
    print("\n" + "=" * 65)
    print("🏛️  CampusFlow — Academic Facility & Event Coordinator")
    print("🌐 Web UI Server berjalan di: http://localhost:8000")
    print("💡 Tekan Ctrl+C di terminal ini untuk mematikan server.")
    print("=" * 65 + "\n")

    # Buka browser secara otomatis jika memungkinkan
    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
