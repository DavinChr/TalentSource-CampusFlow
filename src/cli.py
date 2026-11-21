#!/usr/bin/env python3
"""
CampusFlow — Interactive CLI Demo (Human-in-the-Loop)
====================================================
Antarmuka baris perintah interaktif yang menghubungkan pengguna secara langsung
dengan Otak Agen AI (Google Gemini) dan Graf Status Orkestrasi LangGraph.

Fitur Utama:
1. Human-in-the-Loop: Jika jam tidak diinfokan atau tanggal ambigu, agen secara aktif
   mengajukan pertanyaan klarifikasi ramah sebelum melanjutkan.
2. Eksekusi Deterministik via MCP: Memeriksa ketersediaan, kapasitas, dan integritas fisik
   alat secara transaksional sebelum melakukan penulisan ke database.
3. Transparansi Penuh: Menampilkan jejak audit (Audit Trail) dari setiap keputusan sistem.
"""

import asyncio
from datetime import date
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import warnings

# Redam log verbose dan warning dari pustaka eksternal (google_genai, httpx, httpcore)
warnings.filterwarnings("ignore")
for _log_name in ("google_genai", "google_genai.models", "httpx", "httpcore", "urllib3"):
    logging.getLogger(_log_name).setLevel(logging.ERROR)

# Pastikan encoding output terminal adalah UTF-8 agar tidak error di Windows cp1252
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Pastikan direktori 'src' tidak membayangi (shadow) pustaka 'mcp' resmi dari pip
src_dir = str(Path(__file__).resolve().parent)
while src_dir in sys.path:
    sys.path.remove(src_dir)

# Pastikan root proyek berada dalam sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import dotenv
dotenv.load_dotenv(dotenv_path=BASE_DIR / ".env")

from src.agent.parser import parse_request_text
from src.agent.llm import GeminiAgentClient, LLMBookingExtraction
from src.agent.graph import campusflow_agent
from src.agent.state import new_state
from src.agent.room_recommender import (
    find_room_recommendations,
    format_room_options_prompt,
    resolve_option_selection,
)
from src.agent.early_validator import check_early_constraints


def _merge_extractions(old: Optional[LLMBookingExtraction], new: LLMBookingExtraction) -> LLMBookingExtraction:
    """Menggabungkan data ekstraksi antar-putaran secara kumulatif agar field sebelumnya tidak hilang."""
    if not old:
        return new

    merged_room = new.room_name or old.room_name
    merged_event = new.event_name or old.event_name
    merged_date = new.booking_date or old.booking_date
    merged_date_rel = new.date_relative if new.booking_date else old.date_relative
    merged_date_text = new.date_text or old.date_text
    merged_start = new.start_time or old.start_time
    merged_end = new.end_time or old.end_time
    merged_attendees = new.attendee_count or old.attendee_count
    merged_equipment = list(dict.fromkeys(old.required_equipment + new.required_equipment))

    merged_notes = old.notes
    if new.notes:
        if old.notes and new.notes.strip() not in old.notes:
            merged_notes = f"{old.notes}; {new.notes.strip()}"
        else:
            merged_notes = new.notes.strip()

    # Periksa kelengkapan field pada state gabungan
    missing = []
    if not merged_room:
        missing.append("ruangan")
    if not merged_date:
        missing.append("tanggal")
    if not merged_start:
        missing.append("jam mulai")
    if not merged_end:
        missing.append("jam selesai")

    # Ambiguitas yang masih aktif
    active_ambiguities = []
    for amb in (new.ambiguities or old.ambiguities or []):
        amb_l = amb.lower()
        if merged_start and merged_end and "jam" in amb_l:
            continue
        if merged_date and "tanggal" in amb_l:
            continue
        active_ambiguities.append(amb)

    # Tentukan apakah masih butuh klarifikasi berdasarkan data KUMULATIF
    if not missing and not active_ambiguities:
        needs_clarification = False
        clarification_msg = None
    else:
        needs_clarification = True
        # Cegah bertanya ulang hal yang SUDAH ADA di merged state
        stale_question = False
        if new.clarification_message:
            msg_l = new.clarification_message.lower()
            if merged_start and merged_end and any(w in msg_l for w in ("pukul berapa", "jam mulai", "jam selesai")):
                stale_question = True
            if merged_room and any(w in msg_l for w in ("pilih nomor", "ruangan nomor berapa", "ruangan apa")):
                stale_question = True
            if merged_date and "tanggal berapa" in msg_l:
                stale_question = True

        if new.clarification_message and not stale_question:
            clarification_msg = new.clarification_message
        else:
            parts = []
            if "ruangan" in missing:
                parts.append("pilihan ruangan")
            if "tanggal" in missing:
                parts.append("tanggal acara")
            if "jam mulai" in missing or "jam selesai" in missing:
                parts.append("jam mulai dan selesai (contoh: 08:00 - 11:00)")
            if not merged_attendees:
                parts.append("estimasi jumlah peserta")
            clarification_msg = f"Baik, data pemesanan telah dicatat. Mohon lengkapi info: {', '.join(parts)}."

    return LLMBookingExtraction(
        room_name=merged_room,
        event_name=merged_event,
        booking_date=merged_date,
        date_relative=merged_date_rel,
        date_text=merged_date_text,
        start_time=merged_start,
        end_time=merged_end,
        attendee_count=merged_attendees,
        required_equipment=merged_equipment,
        notes=merged_notes,
        missing_fields=missing,
        ambiguities=active_ambiguities,
        needs_clarification=needs_clarification,
        clarification_message=clarification_msg,
    )


def _deterministic_extract(
    user_msg: str,
    today_str: str,
    prev_extraction: Optional[LLMBookingExtraction] = None,
    active_options: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[LLMBookingExtraction, List[Dict[str, Any]]]:
    """Pengurai deterministik cerdas dengan rekomendasi pilihan ganda ruangan (Human-in-the-Loop)."""
    today = date.fromisoformat(today_str)
    parsed = parse_request_text(user_msg, today)
    ambiguities = list(parsed.get("ambiguities", []))

    # Skema dasar hasil ekstraksi
    fields: Dict[str, Any] = {
        "room_name": parsed.get("room_name"),
        "event_name": parsed.get("event_name"),
        "booking_date": parsed.get("booking_date"),
        "date_relative": parsed.get("date_relative", False),
        "date_text": parsed.get("date_text"),
        "start_time": parsed.get("start_time"),
        "end_time": parsed.get("end_time"),
        "attendee_count": parsed.get("attendee_count"),
        "required_equipment": list(parsed.get("required_equipment", [])),
    }

    # Jika ada data sebelumnya, gabungkan secara kumulatif
    if prev_extraction:
        for k in ["room_name", "event_name", "booking_date", "start_time", "end_time", "attendee_count"]:
            if fields.get(k) is None:
                fields[k] = getattr(prev_extraction, k, None)
        if not fields.get("required_equipment") and prev_extraction.required_equipment:
            fields["required_equipment"] = list(prev_extraction.required_equipment)

    # 1. Cek apakah pengguna memilih nomor opsi dari daftar rekomendasi sebelumnya
    new_options = list(active_options or [])
    if active_options and not fields.get("room_name"):
        selected = resolve_option_selection(user_msg, active_options)
        if selected:
            fields["room_name"] = selected["room_code"]
            new_options = []  # Opsi sudah dipilih

    # 2. Periksa kelengkapan field esensial
    missing = []
    if not fields.get("room_name"): missing.append("ruangan")
    if not fields.get("booking_date"): missing.append("tanggal")
    if not fields.get("start_time"): missing.append("jam mulai")
    if not fields.get("end_time"): missing.append("jam selesai")
    if not fields.get("attendee_count"): missing.append("jumlah peserta")

    needs_clarification = False
    clarification_msg = None

    # 3. Logika Rekomendasi Cerdas (Pilihan Ganda / Opsi Ruangan)
    if not fields.get("room_name"):
        target_attendees = fields.get("attendee_count")
        recs = find_room_recommendations(attendee_count=target_attendees, hint_text=user_msg)
        new_options = recs

        prompt_parts = []
        if recs:
            options_text = format_room_options_prompt(recs, target_attendees, fields.get("event_name"))
            prompt_parts.append(options_text)
        else:
            prompt_parts.append("Mohon informasikan nama atau kode ruangan yang ingin Anda pesan.")

        # Tambahkan pertanyaan untuk data lain yang masih kurang
        pending_data = []
        if not (fields.get("start_time") and fields.get("end_time")):
            pending_data.append("jam acara (contoh: 07:00 - 11:00)")
        if not fields.get("booking_date"):
            pending_data.append("tanggal acara (contoh: 23 September 2026 atau besok)")
        if not fields.get("attendee_count"):
            pending_data.append("estimasi jumlah peserta")

        if pending_data:
            prompt_parts.append(f"\nSerta mohon informasikan: {', '.join(pending_data)}.")

        needs_clarification = True
        clarification_msg = "\n".join(prompt_parts)

    elif not (fields.get("start_time") and fields.get("end_time")):
        needs_clarification = True
        room_info = f"Ruangan dipilih: {fields['room_name']}."
        clarification_msg = f"{room_info} Mohon informasikan jam mulai dan jam selesai acara Anda (contoh: 07:00 sampai 11:00)."

    elif not fields.get("booking_date"):
        needs_clarification = True
        room_info = f"Ruangan dipilih: {fields['room_name']}."
        clarification_msg = f"{room_info} Mohon sebutkan tanggal acara yang diinginkan (contoh: 23 September 2026 atau besok)."

    elif ambiguities:
        needs_clarification = True
        clarification_msg = f"Ada ketidakpastian pada jadwal/ruangan: {', '.join(ambiguities)}. Mohon konfirmasikan kembali."

    extraction = LLMBookingExtraction(
        room_name=fields.get("room_name"),
        event_name=fields.get("event_name"),
        booking_date=fields.get("booking_date"),
        date_relative=fields.get("date_relative", False),
        date_text=fields.get("date_text"),
        start_time=fields.get("start_time"),
        end_time=fields.get("end_time"),
        attendee_count=fields.get("attendee_count"),
        required_equipment=fields.get("required_equipment", []),
        missing_fields=missing,
        ambiguities=ambiguities,
        needs_clarification=needs_clarification,
        clarification_message=clarification_msg,
    )
    return extraction, new_options


def _print_banner():
    print("=" * 72)
    print(" 🎓 CampusFlow — Academic Facility & Event Coordinator")
    print(" 🤖 Powered by Google Gemini & LangGraph (MCP Architecture)")
    print("=" * 72)
    today = os.getenv("SIMULATED_TODAY") or date.today().isoformat()
    print(f"🕒 Tanggal Sistem Aktif : {today}")
    print(f"🧠 Model AI             : {os.getenv('GEMINI_MODEL', 'gemini-flash-latest')}")
    print(f"🏫 Basis Data Kampus    : Universitas Katolik Parahyangan (UNPAR)")
    print("=" * 72)
    print("Ketik instruksi pemesanan Anda dalam bahasa alami.")
    print("Contoh:")
    print("  'Pesan Auditorium Utama PPAG untuk seminar 500 orang pada 23 September 2026 jam 13:00-15:00'")
    print("  'Mau pinjam ruangan untuk kelas 40 orang'        (Rekomendasi ruangan kelas UNPAR)")
    print("  'Mau pinjam lab komputer untuk 30 orang'         (Rekomendasi Lab Komputasi G9)")
    print("(Ketik 'exit' atau 'keluar' untuk mengakhiri sesi)\n")


async def run_interactive_session():
    _print_banner()
    today = os.getenv("SIMULATED_TODAY") or date.today().isoformat()

    llm_client = None
    try:
        llm_client = GeminiAgentClient()
    except Exception as e:
        print(f"ℹ️ Gemini Client: {e}")
        print("💡 Mengaktifkan Mode Parser Deterministik Terstruktur (REQ-NLU-05).\n")

    conversation_history = []

    while True:
        try:
            user_input = input("\n👤 Anda: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSesi diakhiri.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "keluar", "q"):
            print("Terima kasih telah menggunakan CampusFlow.")
            break

        print("\n🔍 Menganalisis permintaan Anda...")

        # 1. Analisis awal menggunakan Gemini atau fallback rekomendasi deterministik
        active_options: List[Dict[str, Any]] = []
        extraction: Optional[LLMBookingExtraction] = None

        conversation_history.append({"role": "user", "content": user_input})

        # 1. Selalu jalankan ekstraksi deterministik untuk mengunci data pasti (waktu, tanggal, alias, alat)
        det_ext, active_options = _deterministic_extract(user_input, today)
        extraction = det_ext

        # 2. Jika klien LLM aktif, perhalus dengan ekstraksi semantik dan teruskan slot terkunci
        if llm_client:
            try:
                llm_ext = llm_client.parse_user_request(
                    user_message=user_input,
                    today=today,
                    conversation_history=conversation_history[:-1],
                    current_extraction=extraction,
                )
                extraction = _merge_extractions(extraction, llm_ext)
            except Exception as e:
                print(f"⚠️ Kuota/Koneksi Gemini bermasalah ({e.__class__.__name__}). Menggunakan parser deterministik.")

        # 2. Early Constraint & Fast-Fail Check:
        # Jika sudah terbukti tidak valid sejak awal (ruang renovasi, kapasitas kurang, alat tidak ada, tanggal lewat, bentrok)
        # langsung tolak dan beritahu pengguna tanpa meminta user mengisi sisa informasi lainnya!
        early_check = check_early_constraints(extraction, today)
        if not early_check["valid"]:
            print(f"\n📋 Status Eksekusi: [{early_check['status']}]")
            print(f"❌ PERMINTAAN DITOLAK / TIDAK DAPAT DIPROSES:")
            print(f"   • {early_check['message']}")
            recs = early_check.get("recommendations", [])
            if recs:
                print("\n💡 Rekomendasi Ruangan Alternatif:")
                for r in recs:
                    bld = f" ({r['building_name']})" if r.get("building_name") else ""
                    print(f"   • [{r.get('option_number', '-')}] {r['room_name']} ({r['room_code']}){bld} — Kapasitas: {r['capacity']} orang")
            print("\n📜 Jejak Audit (Audit Trail):")
            print(f"  🔴 [1] early_constraint_check        -> REJECT  (Status: {early_check['status']})")
            continue

        # 3. Human-in-the-Loop: Tangani kebutuhan klarifikasi interaktif
        accumulated_text = user_input
        while extraction and extraction.needs_clarification:
            print(f"\n🤖 Asisten CampusFlow:\n{extraction.clarification_message}")
            conversation_history.append({"role": "assistant", "content": extraction.clarification_message})

            try:
                clarification_reply = input("\n👤 Jawaban Anda: ").strip()
            except (KeyboardInterrupt, EOFError):
                return

            if clarification_reply.lower() in ("batal", "cancel", "exit"):
                print("Permintaan dibatalkan.")
                break

            conversation_history.append({"role": "user", "content": clarification_reply})
            accumulated_text = f"{accumulated_text}. {clarification_reply}"

            print("\n🔍 Memperbarui data reservasi...")

            # 1. Jalankan ekstraksi deterministik untuk mengunci data pasti (misal waktu, alias ruangan, dll.)
            det_ext, active_options = _deterministic_extract(
                user_msg=clarification_reply,
                today_str=today,
                prev_extraction=extraction,
                active_options=active_options,
            )
            extraction = _merge_extractions(extraction, det_ext)

            # 2. Jika ada LLM, perhalus dengan ekstraksi semantik dan teruskan slot terkunci
            if llm_client:
                try:
                    llm_ext = llm_client.parse_user_request(
                        user_message=clarification_reply,
                        today=today,
                        conversation_history=conversation_history[:-1],
                        current_extraction=extraction,
                    )
                    extraction = _merge_extractions(extraction, llm_ext)
                except Exception:
                    pass

            # Cek kendala dini pada setiap jawaban baru
            early_check = check_early_constraints(extraction, today)
            if not early_check["valid"]:
                print(f"\n📋 Status Eksekusi: [{early_check['status']}]")
                print(f"❌ PERMINTAAN DITOLAK / TIDAK DAPAT DIPROSES:")
                print(f"   • {early_check['message']}")
                recs = early_check.get("recommendations", [])
                if recs:
                    print("\n💡 Rekomendasi Ruangan Alternatif:")
                    for r in recs:
                        bld = f" ({r['building_name']})" if r.get("building_name") else ""
                        print(f"   • [{r.get('option_number', '-')}] {r['room_name']} ({r['room_code']}){bld} — Kapasitas: {r['capacity']} orang")
                print("\n📜 Jejak Audit (Audit Trail):")
                print(f"  🔴 [1] early_constraint_check        -> REJECT  (Status: {early_check['status']})")
                extraction = None
                break

        if not extraction or extraction.needs_clarification:
            continue

        # 4. Data lengkap -> Eksekusi Orkestrasi LangGraph & Server MCP
        print("\n⚙️ Menjalankan orkestrasi alur kerja dan validasi MCP...")
        
        # Buat state awal yang membawa data terurai
        initial_state = new_state(
            request_raw=user_input,
            requester="FAC-001",
            today=today,
            date_confirmed=True,
        )
        parsed = extraction.model_dump()
        parsed["event_name"] = parsed.get("event_name") or "Kegiatan Kampus"
        parsed["attendee_count"] = parsed.get("attendee_count") or 1
        initial_state["parsed_request"] = parsed

        # Jalankan graf status
        final_state = await campusflow_agent.ainvoke(initial_state)

        # 4. Tampilkan Hasil Akhir
        status = final_state["workflow_status"]
        print(f"\n📋 Status Eksekusi: [{status}]")

        if status in ("COMPLETED", "COMPLETED_PARTIAL"):
            ref = final_state.get("booking_reference")
            print(f"✅ RESERVASI BERHASIL! Nomor Referensi: {ref}")
        else:
            print("❌ PERMINTAAN DITOLAK / DIBATALKAN")
            for err in final_state.get("errors", []):
                print(f"   • {err}")

        # 5. Ringkasan Ramah dari Asisten
        print("\n💬 Tanggapan Asisten:")
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
                        "notification_status": final_state.get("notification_status"),
                        "errors": final_state.get("errors", []),
                    },
                    user_message=user_input,
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
                eq_text = " | ".join(eq_parts) if eq_parts else (", ".join(extraction.required_equipment) if extraction.required_equipment else "Standar Ruangan")
                notes_line = f"  • Catatan Khusus   : {extraction.notes}\n" if extraction.notes else ""
                summary = (
                    f"Pemesanan fasilitas berhasil dikonfirmasi!\n"
                    f"  • Nomor Reservasi : {ref}\n"
                    f"  • Ruangan          : {extraction.room_name}\n"
                    f"  • Acara            : {extraction.event_name}\n"
                    f"  • Tanggal & Waktu  : {extraction.booking_date} ({extraction.start_time} - {extraction.end_time})\n"
                    f"  • Jumlah Peserta   : {extraction.attendee_count} orang\n"
                    f"  • Peralatan        : {eq_text} (Telah terverifikasi operasional)\n"
                    f"{notes_line}"
                    f"  • Departemen Notif : Fasilitas Akademik & IT Support"
                )
            else:
                err_text = "\n".join(f"  • {e}" for e in final_state.get("errors", []))
                summary = (
                    f"Permintaan pemesanan tidak dapat disetujui karena kendala berikut:\n{err_text}\n"
                    f"Silakan sesuaikan jadwal atau pilih ruangan alternatif."
                )
        print(summary)

        # 6. Detail Notifikasi Departemen
        notif_details = (final_state.get("notification_details") or {}).get("notifications", [])
        if notif_details:
            print("\n📬 Notifikasi Departemen Kampus:")
            for nd in notif_details:
                n_id = nd.get("notification_id", "-")
                dept = nd.get("department") or nd.get("department_key", "-")
                print(f"  ✉️ [{n_id}] {dept} (Status: TERKIRIM)")
            print(f"  📁 Log tersimpan di: data/filesystem/notifications_outbox.txt")

        # 7. Ringkasan Jejak Audit (Audit Trail)
        print("\n📜 Jejak Audit (Audit Trail):")
        for step in final_state.get("audit_trail", []):
            dec_color = "🟢" if step["decision"] == "PASS" else ("🟡" if step["decision"] == "PARTIAL" else "🔴")
            print(f"  {dec_color} [{step['step_index']}] {step['step_name']:<22} -> {step['decision']:<7} (Status: {step['next_state']})")


if __name__ == "__main__":
    asyncio.run(run_interactive_session())
