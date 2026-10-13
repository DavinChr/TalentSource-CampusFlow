"""
CampusFlow — Integrasi LLM (Google Gemini Integration)
======================================================
Modul ini menghubungkan alur kerja agen dengan model AI Gemini

Fungsi:
1. Membantu ekstrak informasi dari pengguna secara lebih fleksibel
2. Membantu menanyakan kembali informasi yang hilang (Human-in-the-Loop)
   secara sopan jika jam atau tanggal belum jelas
3. Menyusun ringkasan konfirmasi pemesanan akhir yang ramah kepada pengguna
"""

from datetime import date
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import dotenv
from google import genai
from pydantic import BaseModel, Field

# Muat variabel lingkungan dari file .env (berisi API key)
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
dotenv.load_dotenv(dotenv_path=ENV_PATH)

#  DAFTAR RUANGAN
KNOWN_ROOMS = {
    "AUD-01": "Auditorium Utama (Kapasitas: 300 orang)",
    "SR-101": "Ruang Seminar 101 (Kapasitas: 50 orang)",
    "SR-102": "Ruang Seminar 102 (Kapasitas: 50 orang)",
    "CR-301": "Ruang Konferensi Eksekutif (Kapasitas: 20 orang)",
    "LH-201": "Ruang Kuliah 201 (Kapasitas: 80 orang)",
    "LH-202": "Ruang Kuliah 202 (Kapasitas: 120 orang)",
    "LAB-401": "Laboratorium Komputer (Kapasitas: 40 orang)",
    "SR-ENG1": "Ruang Seminar Teknik (Kapasitas: 30 orang)",
}

#  DAFTAR PERALATAN
KNOWN_EQUIPMENT = [
    "projector",
    "microphone",
    "sound_system",
    "smartboard",
    "whiteboard",
    "video_conferencing",
]

# Definisi skema output
class LLMBookingExtraction(BaseModel):
    """
    Format output terstruktur dari AI agar hasil parsing konsisten dan tidak halusinasi.
    """
    room_name: Optional[str] = Field(
        default=None,
        description="Kode ruangan kanonik kampus (mis. 'AUD-01', 'SR-101') atau None jika tidak spesifik/ambigu",
    )
    event_name: Optional[str] = Field(
        default=None,
        description="Nama acara atau kegiatan (mis. 'workshop AI', 'rapat koordinasi')",
    )
    booking_date: Optional[str] = Field(
        default=None,
        description="Tanggal pemesanan dalam format ISO YYYY-MM-DD atau None jika belum pasti/ambigu",
    )
    date_relative: bool = Field(
        default=False,
        description="True jika tanggal diekstrak dari kata relatif ('besok', 'Selasa depan', 'lusa')",
    )
    date_text: Optional[str] = Field(
        default=None,
        description="Frasa asli pengguna untuk tanggal (mis. 'Selasa depan', 'besok')",
    )
    start_time: Optional[str] = Field(
        default=None,
        description="Jam mulai dalam format 24 jam HH:MM (mis. '09:00') atau None jika tidak diinfokan pengguna",
    )
    end_time: Optional[str] = Field(
        default=None,
        description="Jam selesai dalam format 24 jam HH:MM (mis. '11:00') atau None jika tidak diinfokan pengguna",
    )
    attendee_count: Optional[int] = Field(
        default=None,
        description="Estimasi jumlah peserta (orang/pax) atau None jika tidak disebutkan",
    )
    required_equipment: List[str] = Field(
        default_factory=list,
        description="Daftar tipe alat yang diminta pengguna, subset dari: projector, microphone, sound_system, smartboard, whiteboard, video_conferencing",
    )
    missing_fields: List[str] = Field(
        default_factory=list,
        description="Daftar field esensial yang masih belum disediakan pengguna (mis. 'start_time', 'end_time', 'attendee_count')",
    )
    ambiguities: List[str] = Field(
        default_factory=list,
        description="Catatan jika ada ketaksaan/ambiguitas tanggal atau jam",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Catatan tambahan atau instruksi khusus dari pengguna",
    )
    needs_clarification: bool = Field(
        default=False,
        description="True jika ada field wajib yang hilang (terutama jam) sehingga perlu bertanya balik ke pengguna",
    )
    clarification_message: Optional[str] = Field(
        default=None,
        description="Kalimat tanya ramah dalam bahasa Indonesia untuk menanyakan info yang hilang kepada pengguna",
    )

# Client AI
class GeminiAgentClient:
    """Klien AI Google Gemini untuk membantu agen CampusFlow."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-flash-latest")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY belum disetel! Harap masukkan API key di file .env."
            )
        self.client = genai.Client(api_key=self.api_key)

    def parse_user_request(
        self,
        user_message: str,
        today: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> LLMBookingExtraction:
        """Mengekstrak informasi pemesanan menggunakan AI dengan jaminan skema terstruktur."""
        system_instruction = f"""Anda adalah asisten AI fasilitas kampus akademik CampusFlow.
Tugas Anda adalah memahami permintaan reservasi fasilitas/ruangan kampus dari pengguna secara cermat dan teliti.

KONTEKS SISTEM:
- Tanggal hari ini (today): {today}
- Ruangan resmi di kampus:
{json.dumps(KNOWN_ROOMS, indent=2, ensure_ascii=False)}
- Tipe peralatan yang dikenali: {KNOWN_EQUIPMENT}

ATURAN PENTING:
1. JANGAN PERNAH MENEBAK ATAU BERHALUSINASI TENTANG JAM ACARA!
   Jika pengguna TIDAK menyebutkan jam mulai atau jam selesai, jangan isi 'start_time' atau 'end_time'.
   Tandai `needs_clarification = True` dan buat `clarification_message` yang menanyakan jam acara kepada pengguna.
2. AMBIGUITAS TANGGAL RELATIF:
   Jika pengguna menyebutkan frasa seperti "Selasa depan" atau tanggal yang ambigu,
   set `needs_clarification = True`, dan tanyakan kepastian tanggalnya kepada pengguna.
3. JIKA SUDAH LENGKAP:
   Jika seluruh data penting (ruangan, tanggal, jam mulai, jam selesai, jumlah peserta) sudah jelas,
   set `needs_clarification = False` dan `clarification_message = None`.
"""

        contents = []
        if conversation_history:
            for turn in conversation_history:
                contents.append(f"{turn.get('role', 'user')}: {turn.get('content', '')}")
        contents.append(f"Permintaan pengguna saat ini: {user_message}")

        full_prompt = "\n".join(contents)

        candidate_models = [self.model, "gemini-3.5-flash-lite", "gemini-3.7-flash", "gemini-flash-latest"]
        unique_models = list(dict.fromkeys(m for m in candidate_models if m))

        last_error = None
        for m in unique_models:
            try:
                response = self.client.models.generate_content(
                    model=m,
                    contents=full_prompt,
                    config={
                        "system_instruction": system_instruction,
                        "response_mime_type": "application/json",
                        "response_schema": LLMBookingExtraction,
                        "temperature": 0.1,  # Rendah agar deterministik dan presisi
                    },
                )
                raw_text = response.text or "{}"
                return LLMBookingExtraction.model_validate_json(raw_text)
            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(f"Gagal memanggil model Gemini: {last_error}")

    def format_final_summary(
        self,
        state_dict: Dict[str, Any],
        user_message: str,
    ) -> str:
        """Menyusun pesan ringkasan akhir yang ramah kepada pengguna berdasarkan hasil reservasi."""
        prompt = f"""Sebagai asisten resmi CampusFlow, berikan tanggapan yang sopan, profesional, dan jelas dalam Bahasa Indonesia kepada pengguna.

Hasil Eksekusi Alur Kerja:
{json.dumps(state_dict, indent=2, default=str, ensure_ascii=False)}

Instruksi Asli Pengguna:
"{user_message}"

Instruksi Format:
- Jika sukses (COMPLETED / CONFIRMED): Sebutkan nomor referensi pemesanan (booking_reference), ruangan, tanggal, jam, jumlah peserta, dan peralatan yang telah diverifikasi.
- Jika ditolak / gagal: Jelaskan alasan spesifik penolakannya secara transparan berdasarkan bukti audit (misal: bentrok jadwal, kapasitas kurang, atau alat rusak).
"""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "temperature": 0.3,
            },
        )
        return (response.text or "").strip()


if __name__ == "__main__":
    print("=" * 70)
    print(" CampusFlow - Sesi Obrolan Interaktif dengan AI (Gemini)")
    print(" Ketik pesan pemesanan Anda (atau ketik 'keluar' / 'exit' untuk selesai)")
    print("=" * 70)

    client = GeminiAgentClient()
    today_str = date.today().isoformat()
    conversation_history = []

    while True:
        try:
            user_input = input("\nAnda: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSesi diakhiri.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "keluar", "q"):
            print("Sampai jumpa! Sesi obrolan selesai.")
            break

        print("CampusFlow sedang berpikir...")
        try:
            hasil = client.parse_user_request(
                user_message=user_input,
                today=today_str,
                conversation_history=conversation_history,
            )

            # Jika butuh klarifikasi (misal jam atau tanggal belum lengkap)
            if hasil.needs_clarification and hasil.clarification_message:
                print(f"\nAsisten: {hasil.clarification_message}")
                conversation_history.append({"role": "user", "content": user_input})
                conversation_history.append({"role": "assistant", "content": hasil.clarification_message})
            else:
                # Data pemesanan sudah lengkap
                print("\nAsisten: Baik, seluruh data pemesanan telah lengkap!")
                print(f"  - Ruangan   : {hasil.room_name or '-'}")
                print(f"  - Acara     : {hasil.event_name or '-'}")
                print(f"  - Tanggal   : {hasil.booking_date or '-'}")
                print(f"  - Waktu     : {hasil.start_time or '-'} s/d {hasil.end_time or '-'}")
                print(f"  - Peserta   : {hasil.attendee_count or '-'} orang")
                if hasil.required_equipment:
                    print(f"  - Peralatan : {', '.join(hasil.required_equipment)}")
                if hasil.notes:
                    print(f"  - Catatan   : {hasil.notes}")
                print("\n(Data siap divalidasi ke basis data)")

                conversation_history.append({"role": "user", "content": user_input})
                conversation_history.append({"role": "assistant", "content": "Data pemesanan telah lengkap."})
        except Exception as e:
            print(f"Terjadi kesalahan: {e}")


