#!/usr/bin/env python3
"""
CampusFlow — Notification MCP Server (campusflow-notification)
==============================================================
Server MCP resmi untuk menyimulasikan sistem perutean dan pengiriman notifikasi
internal kampus ke departemen-departemen terkait via protokol Model Context Protocol (stdio).

Departemen Resmi:
- academic_facilities : Fasilitas Akademik (reservasi ruangan sukses)
- it_support          : Dukungan TI & Multimedia (alat, proyektor, audio)
- maintenance         : Pemeliharaan & Perbaikan (kerusakan fasilitas, servis)
- event_affairs       : Biro Acara & Protokoler (eskalasi acara besar)
"""

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from mcp.server.mcpserver import MCPServer

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTBOX_PATH = BASE_DIR / "data" / "filesystem" / "notifications_outbox.txt"

server = MCPServer("campusflow-notification")

# -----------------------------------------------------------------------------
# Tabel Perutean Departemen Kampus
# -----------------------------------------------------------------------------
DEPARTMENTS: Dict[str, Dict[str, str]] = {
    "academic_facilities": {
        "name": "Fasilitas Akademik",
        "email": "facilities@campusflow.test",
        "description": "Pengelolaan gedung, ruangan, dan perizinan jadwal umum",
    },
    "it_support": {
        "name": "Dukungan TI & Multimedia",
        "email": "it.support@campusflow.test",
        "description": "Peralatan presentasi, proyektor, jaringan, dan audio",
    },
    "maintenance": {
        "name": "Pemeliharaan & Perbaikan",
        "email": "maintenance@campusflow.test",
        "description": "Perbaikan fisik, fasilitas rusak, dan kendala teknis darurat",
    },
    "event_affairs": {
        "name": "Biro Acara & Protokoler",
        "email": "events@campusflow.test",
        "description": "Koordinasi acara besar, tamu rektorat, dan logistik khusus",
    },
    "campus_security": {
        "name": "Unit Keamanan & Ketertiban Kampus",
        "email": "security@campusflow.test",
        "description": "Pengamanan gedung, izin lembur di luar jam kerja normal, dan akses akhir pekan",
    },
}

# Penyimpanan in-memory riwayat notifikasi sesi
_NOTIFICATIONS: Dict[str, Dict[str, Any]] = {}
_SEQ_COUNTER: int = 0


# =============================================================================
# Tool 1: send_department_notification
# =============================================================================
@server.tool()
def send_department_notification(
    department_key: str,
    subject: str,
    payload: Dict[str, Any],
    booking_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Mengirimkan notifikasi pesan ke departemen kampus terkait.
    
    Args:
        department_key: Kunci departemen ('academic_facilities', 'it_support', 'maintenance', 'event_affairs').
        subject: Judul pesan notifikasi.
        payload: Objek data detail informasi reservasi atau masalah teknis.
        booking_id: ID booking database opsional jika terhubung ke reservasi tertentu.
        
    Returns:
        Status pengiriman (SENT atau FAILED) dan ID notifikasi unik.
    """
    global _SEQ_COUNTER
    dept_clean = department_key.strip().lower()

    if dept_clean not in DEPARTMENTS:
        return {
            "status": "INVALID_DEPARTMENT",
            "message": f"Departemen '{department_key}' tidak valid. Pilihan: {list(DEPARTMENTS.keys())}",
        }

    # Simulasi kegagalan untuk menguji skenario error handling agen (Test Scenario 7)
    if payload.get("simulate_failure") is True:
        return {
            "status": "FAILED",
            "message": "Layanan notifikasi gateway departemen tidak merespons (timeout simulasi).",
        }

    _SEQ_COUNTER += 1
    year = datetime.now().year
    notif_id = f"N-{year}-{_SEQ_COUNTER:03d}"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    entry = {
        "notification_id": notif_id,
        "department_key": dept_clean,
        "department_name": DEPARTMENTS[dept_clean]["name"],
        "target_email": DEPARTMENTS[dept_clean]["email"],
        "subject": subject.strip(),
        "payload": payload,
        "booking_id": booking_id,
        "status": "SENT",
        "sent_at": now_iso,
    }

    _NOTIFICATIONS[notif_id] = entry

    # Catat log notifikasi ke berkas fisik lokal agar transparan & dapat diaudit
    try:
        OUTBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
        log_line = (
            f"[{now_iso}] ID: {notif_id} | TO: {DEPARTMENTS[dept_clean]['name']} <{DEPARTMENTS[dept_clean]['email']}> | "
            f"SUBJ: {subject.strip()} | PAYLOAD: {json.dumps(payload, ensure_ascii=False)}\n"
        )
        with open(OUTBOX_PATH, "a", encoding="utf-8") as f:
            f.write(log_line)

        # REQ-NTF-03: Simpan berkas notifikasi JSON mandiri berformat N-YYYY-NNN.json
        notif_dir = BASE_DIR / "data" / "filesystem" / "notifications"
        notif_dir.mkdir(parents=True, exist_ok=True)
        with open(notif_dir / f"{notif_id}.json", "w", encoding="utf-8") as fj:
            json.dump(entry, fj, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return {
        "status": "SENT",
        "notification_id": notif_id,
        "department_key": dept_clean,
        "department": DEPARTMENTS[dept_clean]["name"],
        "sent_at": now_iso,
    }


# =============================================================================
# Tool 2: get_notification_status
# =============================================================================
@server.tool()
def get_notification_status(notification_id: str) -> Dict[str, Any]:
    """
    Memeriksa status pengiriman dan metadata notifikasi berdasarkan ID.
    
    Args:
        notification_id: ID unik notifikasi (contoh: 'N-2026-001').
    """
    clean_id = notification_id.strip().upper()
    if clean_id not in _NOTIFICATIONS:
        return {
            "found": False,
            "notification_id": clean_id,
            "message": f"Notifikasi '{clean_id}' tidak ditemukan dalam sistem.",
        }

    item = _NOTIFICATIONS[clean_id]
    return {
        "found": True,
        "notification_id": item["notification_id"],
        "department": item["department_name"],
        "subject": item["subject"],
        "status": item["status"],
        "sent_at": item["sent_at"],
        "booking_id": item["booking_id"],
    }


# =============================================================================
# Tool 3: list_department_notifications
# =============================================================================
@server.tool()
def list_department_notifications(
    department_key: str,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Mengambil daftar riwayat pesan yang telah dikirim ke departemen tertentu.
    
    Args:
        department_key: Kunci departemen yang ingin dicek antreannya.
        limit: Batas maksimal jumlah riwayat yang dikembalikan (default: 10).
    """
    dept_clean = department_key.strip().lower()
    if dept_clean not in DEPARTMENTS:
        return {
            "department": dept_clean,
            "total": 0,
            "notifications": [],
            "message": f"Departemen '{department_key}' tidak terdaftar.",
        }

    matched = [
        n for n in _NOTIFICATIONS.values()
        if n["department_key"] == dept_clean
    ]
    # Ambil notifikasi terbaru terlebih dahulu
    matched_sorted = sorted(matched, key=lambda x: x["sent_at"], reverse=True)[:limit]

    return {
        "department": DEPARTMENTS[dept_clean]["name"],
        "department_key": dept_clean,
        "total": len(matched),
        "returned": len(matched_sorted),
        "notifications": matched_sorted,
    }


# =============================================================================
# Suite Uji Mandiri (Self-Check Harness)
# =============================================================================
async def run_self_check() -> bool:
    """Menjalankan verifikasi mandiri terhadap seluruh tool server notifikasi."""
    print("Menjalankan self-check campusflow-notification...")
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

    # Uji 1: Kirim notifikasi sukses ke Fasilitas Akademik
    test_notif_id = ""
    def _check_send(d):
        nonlocal test_notif_id
        test_notif_id = d.get("notification_id", "")
        return d.get("status") == "SENT" and test_notif_id.startswith("N-")

    await _test(
        "send_department_notification() sukses mengirim ke academic_facilities",
        server.call_tool("send_department_notification", {
            "department_key": "academic_facilities",
            "subject": "Reservasi Terkonfirmasi: Workshop AI",
            "payload": {"booking_reference": "BK-2026-001", "attendees": 100},
            "booking_id": 1,
        }),
        _check_send,
    )

    # Uji 2: Cek status notifikasi yang baru saja terkirim
    await _test(
        "get_notification_status() menemukan notifikasi terdaftar",
        server.call_tool("get_notification_status", {"notification_id": test_notif_id}),
        lambda d: d.get("found") is True and d.get("status") == "SENT",
    )

    # Uji 3: List notifikasi departemen academic_facilities
    await _test(
        "list_department_notifications() memuat riwayat pesan",
        server.call_tool("list_department_notifications", {"department_key": "academic_facilities"}),
        lambda d: d.get("total") >= 1 and len(d.get("notifications", [])) >= 1,
    )

    # Uji 4: Penolakan departemen tidak valid
    await _test(
        "send_department_notification() menolak departemen tidak valid",
        server.call_tool("send_department_notification", {
            "department_key": "invalid_dept",
            "subject": "Test",
            "payload": {},
        }),
        lambda d: d.get("status") == "INVALID_DEPARTMENT",
    )

    # Uji 5: Simulasi kegagalan pengiriman (Test Scenario 7 support)
    await _test(
        "send_department_notification() mendukung simulasi kegagalan",
        server.call_tool("send_department_notification", {
            "department_key": "maintenance",
            "subject": "Laporan Proyektor Rusak",
            "payload": {"simulate_failure": True},
        }),
        lambda d: d.get("status") == "FAILED",
    )

    print(f"Hasil self-check: {'SELURUH PENGUJIAN LOLOS' if all_ok else 'ADA KEGAGALAN'}")
    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="CampusFlow Notification MCP Server")
    parser.add_argument("--test", action="store_true", help="Jalankan rangkaian uji mandiri internal")
    args = parser.parse_args()

    if args.test:
        success = asyncio.run(run_self_check())
        sys.exit(0 if success else 1)

    # Menjalankan server via stdio transport (default MCP)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
