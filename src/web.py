#!/usr/bin/env python3
"""
CampusFlow — Web Application Interface
======================================
Server web Starlette/Uvicorn yang menyediakan antarmuka visual sederhana
untuk orkestrasi asisten CampusFlow, visualisasi jejak audit LangGraph,
dan pemantauan notifikasi departemen kampus secara real-time.
"""

import asyncio
from datetime import date, datetime
import json
import logging
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any, Dict, List, Optional
import warnings

# Redam log eksternal
warnings.filterwarnings("ignore")
for _log in ("google_genai", "google_genai.models", "httpx", "httpcore", "urllib3"):
    logging.getLogger(_log).setLevel(logging.ERROR)

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import dotenv
dotenv.load_dotenv(dotenv_path=BASE_DIR / ".env")

from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from src.agent.llm import GeminiAgentClient, LLMBookingExtraction
from src.agent.graph import campusflow_agent
from src.agent.state import new_state
from src.agent.early_validator import check_early_constraints
from src.cli import (
    _merge_extractions,
    _deterministic_extract,
    find_room_recommendations,
    format_room_options_prompt,
    resolve_option_selection,
)

HTML_FILE = BASE_DIR / "src" / "templates" / "index.html"
OUTBOX_PATH = BASE_DIR / "data" / "filesystem" / "notifications_outbox.txt"
DB_PATH = BASE_DIR / "data" / "database" / "campusflow.db"

# Inisialisasi Klien LLM
llm_client: Optional[GeminiAgentClient] = None
try:
    llm_client = GeminiAgentClient()
except Exception:
    llm_client = None

# Penyimpanan sesi in-memory
sessions: Dict[str, Dict[str, Any]] = {}


def _get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in sessions:
        sessions[session_id] = {
            "extraction": None,
            "conversation_history": [],
            "active_options": [],
        }
    return sessions[session_id]


async def handle_index(request: Request):
    """Menyajikan halaman UI utama."""
    if not HTML_FILE.exists():
        return JSONResponse({"error": "Template HTML tidak ditemukan."}, status_code=404)
    return FileResponse(HTML_FILE)


async def handle_chat(request: Request):
    """Endpoint percakapan multi-turn dan eksekusi LangGraph."""
    body = await request.json()
    user_msg = (body.get("message") or "").strip()
    session_id = body.get("session_id") or "default"
    custom_today = body.get("today")

    if not user_msg:
        return JSONResponse({"error": "Pesan tidak boleh kosong."}, status_code=400)

    session = _get_session(session_id)
    history = session["conversation_history"]
    extraction: Optional[LLMBookingExtraction] = session["extraction"]
    active_options: List[Dict[str, Any]] = session["active_options"]

    today = custom_today or date.today().isoformat()
    history.append({"role": "user", "content": user_msg})

    # Cek pemilihan opsi nomor sebelumnya (misal [1], [2], dll.)
    selected_option = resolve_option_selection(user_msg, active_options)
    if selected_option and extraction:
        extraction.room_name = selected_option["room_code"]
        active_options = []
        session["active_options"] = []

    # Ekstraksi dan penggabungan state kumulatif
    if llm_client:
        try:
            new_ext = llm_client.parse_user_request(
                user_message=user_msg,
                today=today,
                conversation_history=history[:-1],
            )
            extraction = _merge_extractions(extraction, new_ext)
        except Exception:
            det_ext, active_options = _deterministic_extract(
                user_msg=user_msg,
                today_str=today,
                prev_extraction=extraction,
                active_options=active_options,
            )
            extraction = _merge_extractions(extraction, det_ext)
    else:
        det_ext, active_options = _deterministic_extract(
            user_msg=user_msg,
            today_str=today,
            prev_extraction=extraction,
            active_options=active_options,
        )
        extraction = _merge_extractions(extraction, det_ext)

    session["extraction"] = extraction

    # 0. Early Constraint & Fast-Fail Check:
    # Jika sudah terbukti tidak valid sejak awal (ruang renovasi, kapasitas kurang, alat tidak ada, tanggal lewat, bentrok)
    # langsung tolak dan beritahu pengguna beserta rekomendasi tanpa meminta user mengisi sisa informasi lainnya!
    early_check = check_early_constraints(extraction, today)
    if not early_check["valid"]:
        msg = f"❌ {early_check['message']}"
        recs = early_check.get("recommendations", [])
        if recs:
            msg += "\n\n💡 Rekomendasi Ruangan Alternatif:\n"
            for r in recs:
                bld = f" ({r['building_name']})" if r.get("building_name") else ""
                msg += f"• [{r.get('option_number', '-')}] {r['room_name']} ({r['room_code']}){bld} — Kapasitas: {r['capacity']} orang\n"
            msg += "\nSilakan pilih nomor opsi rekomendasi di atas atau sebutkan nama ruangan alternatif."

        history.append({"role": "assistant", "content": msg})
        session["active_options"] = recs
        session["extraction"] = None  # Reset karena permintaan invalid

        return JSONResponse({
            "status": early_check["status"],
            "reply": msg,
            "options": recs,
            "booking": extraction.model_dump() if extraction else {},
            "audit_trail": [{
                "step_index": 1,
                "step_name": "early_constraint_check",
                "decision": "REJECT",
                "next_state": early_check["status"],
            }],
            "notifications": [],
            "equipment_results": [],
            "errors": [early_check["message"]],
        })

    # 1. Jika masih butuh klarifikasi (Human-in-the-Loop)
    if not extraction or extraction.needs_clarification:
        # Jika belum ada ruangan, buat rekomendasi cerdas
        if not extraction.room_name:
            target_pax = extraction.attendee_count
            active_options = find_room_recommendations(attendee_count=target_pax, hint_text=user_msg)
            session["active_options"] = active_options
        else:
            active_options = []
            session["active_options"] = []

        clarification_msg = extraction.clarification_message if extraction else None
        if not clarification_msg:
            if active_options:
                clarification_msg = format_room_options_prompt(active_options, extraction.attendee_count, extraction.event_name)
            else:
                clarification_msg = "Mohon lengkapi detail pemesanan seperti ruangan, tanggal, atau jam acara."

        history.append({"role": "assistant", "content": clarification_msg})

        return JSONResponse({
            "status": "NEEDS_CLARIFICATION",
            "reply": clarification_msg,
            "options": active_options,
            "booking": extraction.model_dump() if extraction else {},
            "audit_trail": [],
            "notifications": [],
            "equipment_results": [],
            "errors": [],
        })

    # 2. Data lengkap -> Eksekusi Graf Orkestrasi LangGraph & MCP
    initial_state = new_state(
        request_raw=user_msg,
        requester="FAC-001",
        today=today,
        date_confirmed=True,
    )
    parsed = extraction.model_dump()
    parsed["event_name"] = parsed.get("event_name") or "Kegiatan Kampus"
    parsed["attendee_count"] = parsed.get("attendee_count") or 1
    initial_state["parsed_request"] = parsed

    final_state = await campusflow_agent.ainvoke(initial_state)
    status = final_state["workflow_status"]

    # Buat ringkasan ramah
    summary = None
    if llm_client:
        try:
            summary = llm_client.format_final_summary(
                state_dict={
                    "workflow_status": status,
                    "booking_reference": final_state.get("booking_reference"),
                    "room_name": extraction.room_name,
                    "event_name": extraction.event_name,
                    "booking_date": extraction.booking_date,
                    "start_time": extraction.start_time,
                    "end_time": extraction.end_time,
                    "attendee_count": extraction.attendee_count,
                    "notes": extraction.notes,
                    "equipment_status": final_state.get("equipment_status"),
                    "equipment_results": final_state.get("equipment_results"),
                    "notification_status": final_state.get("notification_status"),
                    "errors": final_state.get("errors", []),
                },
                user_message=user_msg,
            )
        except Exception:
            summary = None

    if not summary:
        if status in ("COMPLETED", "COMPLETED_PARTIAL"):
            ref = final_state.get("booking_reference")
            eq_results = final_state.get("equipment_results") or []
            add_ons = [eq.get("equipment_name", eq.get("equipment_code")) for eq in eq_results if eq.get("is_add_on")]
            built_ins = [eq.get("equipment_name", eq.get("equipment_code")) for eq in eq_results if not eq.get("is_add_on")]
            eq_parts = []
            if built_ins:
                eq_parts.append(f"Built-in: {', '.join(built_ins)}")
            if add_ons:
                eq_parts.append(f"Add-on (disiapkan IT Support): {', '.join(add_ons)}")
            eq_text = " | ".join(eq_parts) if eq_parts else "Standar Ruangan"

            summary = (
                f"Pemesanan fasilitas berhasil dikonfirmasi!\n"
                f"• Nomor Reservasi: {ref}\n"
                f"• Ruangan: {extraction.room_name}\n"
                f"• Acara: {extraction.event_name}\n"
                f"• Jadwal: {extraction.booking_date} ({extraction.start_time} - {extraction.end_time})\n"
                f"• Peserta: {extraction.attendee_count} orang\n"
                f"• Peralatan: {eq_text}"
            )
            if extraction.notes:
                summary += f"\n• Catatan Khusus: {extraction.notes}"
        else:
            err_text = "\n".join(f"• {e}" for e in final_state.get("errors", []))
            summary = f"Permintaan pemesanan belum dapat diproses karena:\n{err_text}"

    history.append({"role": "assistant", "content": summary})

    # Reset extraction untuk pemesanan berikutnya pada sesi ini
    session["extraction"] = None
    session["active_options"] = []

    notifications = (final_state.get("notification_details") or {}).get("notifications", [])

    return JSONResponse({
        "status": status,
        "reply": summary,
        "booking_reference": final_state.get("booking_reference"),
        "booking": parsed,
        "audit_trail": final_state.get("audit_trail", []),
        "notifications": notifications,
        "equipment_results": final_state.get("equipment_results", []),
        "errors": final_state.get("errors", []),
    })


async def handle_reset(request: Request):
    """Mereset riwayat sesi percakapan."""
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    session_id = body.get("session_id") or "default"
    if session_id in sessions:
        sessions[session_id] = {
            "extraction": None,
            "conversation_history": [],
            "active_options": [],
        }
    return JSONResponse({"status": "RESET", "session_id": session_id})


async def handle_get_notifications(request: Request):
    """Membaca daftar riwayat notifikasi departemen dari outbox berkas fisik."""
    if not OUTBOX_PATH.exists():
        return JSONResponse({"notifications": []})

    entries = []
    line_re = re.compile(r"^\[(.*?)\] ID: (.*?) \| TO: (.*?) \| SUBJ: (.*?) \| PAYLOAD: (.*)$")
    try:
        with open(OUTBOX_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for idx, line in enumerate(reversed(lines)):
            line = line.strip()
            if not line:
                continue
            m = line_re.match(line)
            if m:
                timestamp, n_id, target, subject, payload_str = m.groups()
                try:
                    payload = json.loads(payload_str)
                except Exception:
                    payload = {"raw": payload_str}
                entries.append({
                    "id": n_id.strip(),
                    "timestamp": timestamp.strip(),
                    "to": target.strip(),
                    "subject": subject.strip(),
                    "payload": payload,
                })
            else:
                entries.append({"id": f"RAW-{idx}", "subject": line, "to": "Unknown", "payload": {}})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    return JSONResponse({"notifications": entries[:50]})


async def handle_get_rooms(request: Request):
    """Mengambil katalog ruangan dari database."""
    if not DB_PATH.exists():
        return JSONResponse({"rooms": []})
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT r.id, r.room_code, r.room_name, r.room_type, r.capacity, r.status,
                   b.code as building_code, b.name as building_name
            FROM rooms r
            JOIN buildings b ON b.id = r.building_id
            ORDER BY b.code, r.room_code
        """).fetchall()
        rooms = [dict(r) for r in rows]
        conn.close()
        return JSONResponse({"rooms": rooms})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


routes = [
    Route("/", handle_index, methods=["GET"]),
    Route("/api/chat", handle_chat, methods=["POST"]),
    Route("/api/reset", handle_reset, methods=["POST"]),
    Route("/api/notifications", handle_get_notifications, methods=["GET"]),
    Route("/api/rooms", handle_get_rooms, methods=["GET"]),
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
]

app = Starlette(debug=True, routes=routes, middleware=middleware)


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("🚀 CampusFlow Web UI Server Aktif!")
    print("📍 Buka di browser: http://localhost:8000")
    print("=" * 60 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
