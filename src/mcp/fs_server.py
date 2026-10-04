#!/usr/bin/env python3
"""
CampusFlow — Filesystem MCP Server (campusflow-fs)
==================================================
Server MCP resmi untuk mengakses berkas catatan operasional fasilitas kampus
secara terisolasi dan read-only via protokol Model Context Protocol (stdio).

Fitur Keamanan:
- Akses baca-saja (read-only).
- Sandbox ketat: Hanya berkas di dalam direktori data/filesystem/ yang dapat diakses.
- Proteksi terhadap path traversal (../, path absolut, symlink escape).
- Nilai status deterministik: membedakan secara tegas OPERATIONAL, UNDER_MAINTENANCE,
  FAULTY, DECOMMISSIONED, dan UNKNOWN (tanpa halusinasi).
"""

import argparse
import asyncio
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List

from mcp.server.mcpserver import MCPServer

# -----------------------------------------------------------------------------
# Konfigurasi Path Sandbox
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FS_DIR = (BASE_DIR / "data" / "filesystem").resolve()

STATUS_FILE = FS_DIR / "equipment_status.txt"
LOGS_FILE = FS_DIR / "maintenance_logs.txt"
INVENTORY_FILE = FS_DIR / "equipment_inventory.txt"

server = MCPServer("campusflow-fs")


def _is_safe_filename(filename: str) -> bool:
    """
    Validasi keamanan nama berkas:
    - Tidak boleh mengandung separator direktori ('/' atau '\\').
    - Tidak boleh mengandung pola traversal ('..').
    - Path hasil resolusi harus secara absolut berada di dalam direktori FS_DIR.
    """
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return False
    target_path = (FS_DIR / filename).resolve()
    return target_path.parent == FS_DIR


# =============================================================================
# Tool 1: get_equipment_status
# =============================================================================
@server.tool()
def get_equipment_status(equipment_code: str) -> Dict[str, Any]:
    """
    Mengambil status operasional terkini suatu peralatan dari catatan inspeksi harian.
    
    Args:
        equipment_code: Kode unik peralatan kampus (contoh: 'PRJ-01', 'PRJ-02', 'MIC-01').
        
    Returns:
        Dictionary status operasional (OPERATIONAL, UNDER_MAINTENANCE, FAULTY, atau UNKNOWN).
    """
    clean_code = equipment_code.strip().upper()
    if not STATUS_FILE.exists():
        return {
            "found": False,
            "equipment_code": clean_code,
            "status": "UNKNOWN",
            "message": "Berkas equipment_status.txt tidak ditemukan di filesystem.",
        }

    lines = STATUS_FILE.read_text(encoding="utf-8").splitlines()
    for line in lines:
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("#"):
            continue
        parts = [p.strip() for p in line_clean.split("|")]
        if len(parts) >= 2 and parts[0].upper() == clean_code:
            status_val = parts[1].upper()
            last_updated = parts[2] if len(parts) > 2 else "UNKNOWN"
            notes = parts[3] if len(parts) > 3 else ""
            return {
                "found": True,
                "equipment_code": clean_code,
                "status": status_val,
                "last_updated": last_updated,
                "notes": notes,
            }

    # Jika kode alat tidak ditemukan sama sekali di catatan fisik
    return {
        "found": False,
        "equipment_code": clean_code,
        "status": "UNKNOWN",
        "message": f"Kode peralatan '{clean_code}' tidak terdaftar dalam catatan status operasional.",
    }


# =============================================================================
# Tool 2: search_maintenance_log
# =============================================================================
@server.tool()
def search_maintenance_log(equipment_code: str, keyword: str = "") -> Dict[str, Any]:
    """
    Mencari riwayat catatan servis dan pemeliharaan teknisi untuk peralatan tertentu.
    
    Args:
        equipment_code: Kode peralatan yang dicari (contoh: 'PRJ-02', 'PRJ-04').
        keyword: Kata kunci tambahan opsional untuk memfilter catatan log.
    """
    clean_code = equipment_code.strip().upper()
    filter_kw = keyword.strip().lower()

    if not LOGS_FILE.exists():
        return {
            "found": False,
            "equipment_code": clean_code,
            "log_entries": [],
            "message": "Berkas maintenance_logs.txt tidak ditemukan di filesystem.",
        }

    # Pola format log: [YYYY-MM-DD] KODE | STATUS: <status> | Keterangan
    # Contoh: [2026-09-10] PRJ-02 | STATUS: UNDER_MAINTENANCE | LCD panel retak...
    pattern = re.compile(
        r"^\[(?P<date>\d{4}-\d{2}-\d{2})\]\s+(?P<code>[\w-]+)\s*\|\s*STATUS:\s*(?P<status>\w+)\s*\|\s*(?P<detail>.*)$"
    )

    matched_entries: List[Dict[str, Any]] = []
    lines = LOGS_FILE.read_text(encoding="utf-8").splitlines()

    for line in lines:
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("#"):
            continue

        match = pattern.match(line_clean)
        if match:
            entry_code = match.group("code").upper()
            if entry_code == clean_code:
                detail_text = match.group("detail")
                if filter_kw and filter_kw not in detail_text.lower():
                    continue

                # Ekstrak teknisi jika ada pola "Teknisi: ..."
                technician = "N/A"
                if "Teknisi:" in detail_text:
                    tech_part = detail_text.split("Teknisi:")[1].split(".")[0].strip()
                    technician = tech_part

                matched_entries.append({
                    "date": match.group("date"),
                    "status": match.group("status").upper(),
                    "note": detail_text,
                    "technician": technician,
                })

    return {
        "found": len(matched_entries) > 0,
        "equipment_code": clean_code,
        "log_entries": matched_entries,
        "total_entries": len(matched_entries),
    }


# =============================================================================
# Tool 3: read_file
# =============================================================================
@server.tool()
def read_file(filename: str) -> Dict[str, Any]:
    """
    Membaca seluruh isi berkas teks operasional dari direktori sandbox.
    
    Args:
        filename: Nama berkas teks murni tanpa path direktori (contoh: 'equipment_inventory.txt').
    """
    clean_name = filename.strip()

    # Validasi pencegahan path traversal
    if not _is_safe_filename(clean_name):
        return {
            "error": "ACCESS_DENIED",
            "message": "Akses ditolak: nama berkas tidak valid atau mencoba mengakses di luar sandbox.",
        }

    target_file = FS_DIR / clean_name
    if not target_file.exists() or not target_file.is_file():
        return {
            "error": "FILE_NOT_FOUND",
            "message": f"Berkas '{clean_name}' tidak ditemukan di dalam direktori sandbox.",
        }

    content = target_file.read_text(encoding="utf-8")
    return {
        "filename": clean_name,
        "size_bytes": len(content.encode("utf-8")),
        "content": content,
    }


# =============================================================================
# Suite Uji Mandiri (Self-Check Harness)
# =============================================================================
async def run_self_check() -> bool:
    """Menjalankan verifikasi mandiri terhadap seluruh tool filesystem dan proteksi sandbox."""
    print("Menjalankan self-check campusflow-fs...")
    all_ok = True

    async def _test(name: str, coro, check_fn) -> None:
        nonlocal all_ok
        try:
            res = await coro
            raw_text = res.content[0].text
            data = json.loads(raw_text)
            passed = check_fn(data)
            status = "[PASS]" if passed else "[FAIL]"
            if not passed:
                all_ok = False
            print(f"  {status:<6} {name}")
        except Exception as err:
            all_ok = False
            print(f"  [FAIL] {name}: {err}")

    # Uji 1: Baca status alat operasional normal (PRJ-01)
    await _test(
        "get_equipment_status('PRJ-01') bernilai OPERATIONAL",
        server.call_tool("get_equipment_status", {"equipment_code": "PRJ-01"}),
        lambda d: d.get("found") is True and d.get("status") == "OPERATIONAL",
    )

    # Uji 2: Baca status alat dalam perbaikan (PRJ-02)
    await _test(
        "get_equipment_status('PRJ-02') bernilai UNDER_MAINTENANCE",
        server.call_tool("get_equipment_status", {"equipment_code": "PRJ-02"}),
        lambda d: d.get("found") is True and d.get("status") == "UNDER_MAINTENANCE",
    )

    # Uji 3: Baca status alat rusak untuk uji kontradiksi (PRJ-04)
    await _test(
        "get_equipment_status('PRJ-04') bernilai FAULTY",
        server.call_tool("get_equipment_status", {"equipment_code": "PRJ-04"}),
        lambda d: d.get("found") is True and d.get("status") == "FAULTY",
    )

    # Uji 4: Deteksi alat tidak terdaftar menghasilkan UNKNOWN (tanpa halusinasi)
    await _test(
        "get_equipment_status('UNKNOWN-99') menghasilkan status UNKNOWN",
        server.call_tool("get_equipment_status", {"equipment_code": "UNKNOWN-99"}),
        lambda d: d.get("found") is False and d.get("status") == "UNKNOWN",
    )

    # Uji 5: Cari riwayat servis PRJ-02 di maintenance logs
    await _test(
        "search_maintenance_log('PRJ-02') menemukan catatan LCD retak",
        server.call_tool("search_maintenance_log", {"equipment_code": "PRJ-02"}),
        lambda d: d.get("found") is True and any("LCD" in e.get("note", "") for e in d.get("log_entries", [])),
    )

    # Uji 6: Membaca berkas inventaris yang sah
    await _test(
        "read_file('equipment_inventory.txt') berhasil membaca konten",
        server.call_tool("read_file", {"filename": "equipment_inventory.txt"}),
        lambda d: "PRJ-01" in d.get("content", ""),
    )

    # Uji 7: Proteksi sandbox terhadap path traversal (../)
    await _test(
        "read_file('../../etc/passwd') ditolak dengan ACCESS_DENIED",
        server.call_tool("read_file", {"filename": "../../etc/passwd"}),
        lambda d: d.get("error") == "ACCESS_DENIED",
    )

    # Uji 8: Penolakan file yang tidak ada
    await _test(
        "read_file('nonexistent_file.txt') menghasilkan FILE_NOT_FOUND",
        server.call_tool("read_file", {"filename": "nonexistent_file.txt"}),
        lambda d: d.get("error") == "FILE_NOT_FOUND",
    )

    print(f"Hasil self-check: {'SELURUH PENGUJIAN LOLOS' if all_ok else 'ADA KEGAGALAN'}")
    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="CampusFlow Filesystem MCP Server")
    parser.add_argument("--test", action="store_true", help="Jalankan rangkaian uji mandiri internal")
    args = parser.parse_args()

    if args.test:
        success = asyncio.run(run_self_check())
        sys.exit(0 if success else 1)

    # Menjalankan server via stdio transport (default MCP)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
