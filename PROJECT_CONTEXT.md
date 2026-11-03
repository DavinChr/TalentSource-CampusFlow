# Konteks Proyek: CampusFlow
**Academic Campus Facility & Event Coordinator**
*(Koordinator Fasilitas & Acara Kampus Akademik)*

---

## 1. Tujuan Proyek
**CampusFlow** adalah sistem orkestrasi agen AI otonom yang dirancang untuk mengelola permintaan kampus yang kompleks dan melibatkan banyak departemen menggunakan instruksi bahasa alami (*natural language*). 

Sistem ini **bukan sekadar chatbot biasa**, melainkan sebuah **agen alur kerja otonom yang terkendali (*controlled autonomous workflow agent*)**. Sistem ini mampu:
- Mengurai permintaan pengguna (*request decomposition*).
- Memvalidasi setiap prasyarat secara berurutan di berbagai sumber data terisolasi melalui *Model Context Protocol* (MCP).
- Menegakkan aturan bisnis dan batasan keamanan secara deterministik (pasti dan terukur).
- Melakukan penulisan/pemesanan ke database secara transaksional **hanya setelah semua validasi lulus**.
- Mengirimkan notifikasi ke departemen kampus terkait sesuai alur kerja.

---

## 2. Kondisi Repositori Saat Ini
- **Direktori Utama Proyek:** `D:\TalentSource\CampusFlow`
- **Manajemen Versi:** Git repository terhubung ke GitHub `https://github.com/DavinChr/TalentSource-CampusFlow.git` pada cabang `main`.
- **Struktur Berkas Utama Saat Ini:**
  - `prompts/00_MASTER_PROMPT.md`: Dokumen acuan spesifikasi dan panduan 8 fase pengerjaan.
  - `docs/`:
    - `SRS_CampusFlow.md`: Dokumen Spesifikasi Kebutuhan Perangkat Lunak formal standar IEEE 830-1998 / ISO/IEC/IEEE 29148:2018 (Dokumen ID: `CF-SRS-2026-001`, Draft, 26 September 2026, Penulis: Joseph Davin).
    - `Software Requirements Specification (SRS) - Campus Flow.pdf`: Dokumen PDF formal bersampul dan bernomor halaman terstruktur.
    - Dokumen Desain Sistem: `architecture.md`, `architecture-decisions.md`, `data-model.md`, `mcp-architecture.md`, `problem-definition.md`, `research.md`, `state-machine.md`, `workflow.md`, `campusflow_overview.md`.
  - `data/database/`:
    - `schema.sql`: DDL 6 tabel utama (`buildings`, `rooms`, `equipment`, `room_equipment`, `users`, `bookings`, `audit_logs`) lengkap dengan batasan integritas referensial dan indeks pencarian.
    - `seed.sql`: Data awal realistis untuk 3 gedung, 8 ruangan, 10 perangkat, dan 5 reservasi awal untuk menguji 10 skenario pengujian.
    - `init_db.py`: Skrip inisialisasi basis data idempoten dan pengujian integritas 13 poin (*13-point verification test*).
  - `data/filesystem/`:
    - `equipment_inventory.txt`: Data inventaris aset perangkat kampus.
    - `equipment_status.txt`: Catatan status operasional peralatan secara riil.
    - `maintenance_logs.txt`: Log pemeliharaan berkala untuk pengujian skenario bentrok dan status peralatan.

---

## 3. Tumpukan Teknologi & Lingkungan Eksekusi

### Lingkungan Sistem & Runtime
- **Sistem Operasi:** Windows 11 (PowerShell).
- **Runtime Python:**
  - Versi Utama: Python `3.14.0` (`C:\Python314\`)
  - Versi Cadangan: Python `3.12` (`py -3.12`)
  - *Catatan Penting:* Direktori `site-packages` global bersifat *read-only* untuk hak akses standar, sehingga pustaka proyek wajib diisolasi di dalam *Virtual Environment* lokal (`.venv`).
- **Runtime Node.js:** Node.js `v24.11.1`, npm `11.6.2`.
- **Database Engine:** SQLite 3 (versi 3.50.4 bawaan modul standar Python `sqlite3`), mendukung transaksi ACID, *foreign keys*, dan berjalan mandiri tanpa perlu server database eksternal terpisah.

### Pustaka & Framework Utama
- **Orkestrasi Agen:** `LangGraph` & `langchain-core` untuk membangun mesin status (*state machine*) eksplisit dan alur kerja ReAct.
- **Model Context Protocol (MCP):** SDK resmi Python `mcp` (`mcp>=2.2.0`, `mcp-types`, `pydantic>=2.7.4`), berkomunikasi via protokol standar JSON-RPC 2.0 melalui *stdio*.
- **Validasi Data & Skema:** `pydantic` v2 untuk parsing struktur permintaan pengguna, penegakan skema data, dan model status (*state*).
- **Pengujian (Testing):** `pytest` dan `pytest-asyncio` untuk pengujian unit, integrasi, mock MCP, hingga uji menyeluruh (*end-to-end*).

---

## 4. Desain Arsitektur Server MCP
CampusFlow memerlukan tiga server MCP independen yang saling terisolasi dan berkomunikasi melalui protokol standar MCP (*stdio*):

1. **Server MCP Database (`campusflow-db`):**
   - Fungsi utama: Mengelola data ruangan, kapasitas, jadwal, dan pencatatan reservasi.
   - Perangkat (*tools*) yang disediakan: `inspect_schema`, `query_room_availability`, `query_room_capacity`, `check_booking_conflicts`, `query_equipment`, `create_booking_transactional`.
   - Batasan Keamanan: Menggunakan prinsip *least-privilege*, kueri SQL berparameter, komit/rollback transaksi eksplisit, dan mencegah agen mengeksekusi perintah SQL berbahaya secara sembarangan.
2. **Server MCP Filesystem (`campusflow-fs`):**
   - Fungsi utama: Mengakses file dokumen operasional kampus di `data/filesystem/` (misalnya: catatan pemeliharaan/servis, inventaris perangkat, status alat).
   - Perangkat (*tools*) yang disediakan: `read_file`, `search_maintenance_log`, `get_equipment_status`.
   - Batasan Keamanan: Akses baca saja (*read-only sandbox*) khusus pada folder operasional fasilitas kampus, mencegah pembacaan file sistem lain (*path traversal guard*).
3. **Server MCP Notifikasi Mock API (`campusflow-notification`):**
   - Fungsi utama: Menyimulasikan sistem pesan/notifikasi internal kampus.
   - Perangkat (*tools*) yang disediakan: `send_department_notification`, `get_notification_status`, `list_department_notifications`.
   - Perutean (*Routing*): Mengarahkan pesan ke departemen yang tepat secara terstruktur (Fasilitas Akademik, Dukungan TI, Pemeliharaan, atau Urusan Acara).

---

## 5. Batasan & Aturan Keamanan (Guardrails)

1. **Aturan Mutlak (Non-Negotiable Rule):**
   - **DILARANG MENULIS RESERVASI KE DATABASE SEBELUM SEMUA VALIDASI SELESAI DAN LULUS.**
   - Urutan alur kerja wajib:
     $$\text{Urai Permintaan} \to \text{Validasi Syarat} \to \text{Cek Ketersediaan Ruangan} \to \text{Cek Kapasitas} \to \text{Cek Kebutuhan Alat} \to \text{Verifikasi Status Operasional Alat} \to \text{Otorisasi} \to \text{Tulis DB (Transaksional)} \to \text{Kirim Notifikasi}$$
2. **Logika Bisnis Deterministik vs Penalaran Probabilistik LLM:**
   - LLM hanya dipakai untuk memahami bahasa manusia, mengekstrak maksud pengguna, mengurai tugas, dan menyusun teks penjelasan.
   - Perhitungan kapasitas ruangan, deteksi bentrok jadwal waktu, batasan transaksi database, dan perpindahan status alur kerja dijalankan oleh program secara deterministik (pasti/matematis), bukan ditebak oleh LLM.
3. **Penalaran Berbasis Bukti Nyata (*Evidence-Based Reasoning*):**
   - Agen tidak boleh mengarang (*halusinasi*) kondisi alat atau ketersediaan ruangan.
   - Status harus dibedakan tegas: `AVAILABLE` (Tersedia), `UNAVAILABLE` (Tidak Tersedia), `UNKNOWN` (Tidak Diketahui), dan `ERROR` (Kesalahan). Status `UNKNOWN` dilarang disamakan dengan `AVAILABLE`.
4. **Strategi Tanpa Ketergantungan API Key Berbayar (*Offline Fallback*):**
   - Lingkungan lokal saat ini belum memiliki API key pihak ketiga (`OPENAI_API_KEY`, dll.).
   - Arsitektur mendukung integrasi LLM eksternal via variabel lingkungan (OpenAI, Anthropic, Gemini), namun juga dilengkapi mesin pengurai offline deterministik (*Mock/Deterministic NLU Parser*) agar 10 skenario pengujian otomatis dan demo utama dapat diuji secara mandiri tanpa biaya ataupun limit kuota API.

---

## 6. Status Komponen & Progres Pengerjaan

### Komponen yang Telah Selesai Dibangun:
1. **Dokumentasi Spesifikasi Kebutuhan Formal (IEEE 830-1998 / ISO/IEC/IEEE 29148:2018):**
   - Berkas: `docs/SRS_CampusFlow.md` dan `docs/Software Requirements Specification (SRS) - Campus Flow.pdf` (Dokumen ID: `CF-SRS-2026-001`, Draft, 26 September 2026, Penulis: Joseph Davin).
   - Memuat 7 bab standar: Pengantar, Deskripsi Umum, Antarmuka Eksternal, Kebutuhan Sistem & Fungsional (dengan Mermaid ERD tervalidasi dan Kamus Data), Kebutuhan Non-Fungsional, Matriks Keterlacakan (RTM), serta Rencana Verifikasi & Validasi (10 Skenario Uji).
2. **Dokumentasi Riset & Desain Arsitektur Sistem:**
   - `docs/research.md`, `docs/problem-definition.md`, `docs/architecture-decisions.md` (ADR).
   - `docs/architecture.md`, `docs/workflow.md`, `docs/state-machine.md`, `docs/data-model.md`, `docs/mcp-architecture.md`.
3. **Lapisan Basis Data (Fase 3 - Selesai & Terverifikasi):**
   - Skema DDL: `data/database/schema.sql` (6 tabel: `buildings`, `rooms`, `equipment`, `room_equipment`, `users`, `bookings`, `audit_logs`).
   - Data Benih (*Seed Data*): `data/database/seed.sql` (3 gedung, 8 ruangan, 10 alat, 5 reservasi awal mencakup semua kasus uji bentrok dan kegagalan alat).
   - Skrip Verifikasi: `data/database/init_db.py` (Lolos seluruh 13/13 pengujian integritas, ACID, foreign keys, indeks, dan deteksi konflik tumpang tindih waktu).
4. **Berkas Operasional Filesystem (Fase 3 - Selesai):**
   - `data/filesystem/equipment_inventory.txt`, `data/filesystem/equipment_status.txt`, `data/filesystem/maintenance_logs.txt`.

### Komponen Berikutnya yang Akan Dibangun:
1. **Infrastruktur Server MCP (Fase 4 - Siap Dikerjakan):**
   - `mcp_db_server.py`: Server MCP Database via *stdio* (`inspect_schema`, `query_room_availability`, dll.).
   - `mcp_fs_server.py`: Server MCP Filesystem via *stdio* (`read_file`, `search_maintenance_log`, dll.).
   - `mcp_notification_server.py`: Server MCP Mock API Notifikasi Departemen via *stdio*.
2. **Orkestrasi Alur Kerja Agen LangGraph (Fase 5):** Graf status, simpul ReAct, pengurai NLU, pencatat jejak audit.
3. **Guardrails & Keamanan Deterministik (Fase 6):** Penegakan batasan keamanan dan invariant data.
4. **Pengujian Otomatis 10 Skenario (Fase 7):** Pengujian pytest terisolasi dari Uji 1 hingga Uji 10.
5. **Antarmuka CLI & Skenario Demo (Fase 8):** Skrip demonstrasi CLI interaktif dan audit akhir.

---

## 7. Rencana Eksekusi Berdasarkan Fase

| Fase | Deskripsi | Status | Hasil Keluaran (*Deliverables*) |
|---|---|---|---|
| **Fase 0** | **Inisialisasi Proyek** | **SELESAI** | Audit lingkungan & repositori, `PROJECT_CONTEXT.md`, struktur git |
| **Fase 1** | **Riset & Brainstorming** | **SELESAI** | `docs/research.md`, `docs/problem-definition.md`, `docs/architecture-decisions.md` |
| **Fase 2** | **Desain Sistem Arsitektur & SRS** | **SELESAI** | Dokumen SRS IEEE (`docs/SRS_CampusFlow.md`, `docs/Software Requirements Specification (SRS) - Campus Flow.pdf`), `docs/architecture.md`, `docs/workflow.md`, `docs/state-machine.md`, `docs/data-model.md`, `docs/mcp-architecture.md` |
| **Fase 3** | **Database & Data Uji (Seed Data)** | **SELESAI** | `data/database/schema.sql`, `data/database/seed.sql`, `data/database/init_db.py` (13/13 lolos), berkas operasional `data/filesystem/` |
| **Fase 4** | **Infrastruktur Server MCP** | **SELESAI** | 3 Server MCP Python (`db_server.py`, `fs_server.py`, `notification_server.py`), pengujian integrasi multi-server (`test_mcp_integration.py` 2/2 lolos) |
| **Fase 5** | **Orkestrasi Agen (LangGraph & Gemini LLM)** | **SELESAI** | Graf alur kerja LangGraph (`graph.py`), simpul terisolasi (`nodes/`), integrasi Google GenAI Gemini (`llm.py`), adaptasi Human-in-the-Loop, antarmuka CLI interaktif (`cli.py`), pengujian alur penuh (`test_agent_workflow.py` 5/5 lolos) |
| **Fase 6** | **Guardrails & Uji Keamanan** | **SIAP DIKERJAKAN** | Penegakan invariant keamanan, pencegahan halusinasi, isolasi transaksi |
| **Fase 7** | **Pengujian Otomatis Menyeluruh** | Menunggu Fase 6 | 10 Skenario pengujian otomatis end-to-end (`pytest`) |
| **Fase 8** | **Audit Akhir & Demonstrasi** | Menunggu Fase 7 | Demo CLI kasus utama & kasus gagal, `README.md`, laporan akhir |

---

