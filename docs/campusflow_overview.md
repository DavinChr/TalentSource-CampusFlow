# 🎓 Memahami CampusFlow Secara Menyeluruh
**Panduan Lengkap: Tujuan, Arsitektur, Alur Kerja, dan Rencana Pembangunan**

---

## 🧭 Bagian 1 — Latar Belakang: Masalah Apa yang Dipecahkan?

### Gambaran Situasi di Kampus Saat Ini

Bayangkan kamu adalah seorang dosen yang ingin memesan Auditorium Utama untuk workshop AI besok. Kamu ingin memastikan:
1. Auditorium tidak sedang dipakai orang lain pada jam yang sama
2. Auditorium bisa menampung 100 peserta
3. Proyektor di dalam ruangan dalam kondisi baik

**Masalah nyata yang sering terjadi:**

| Masalah | Dampak |
|---|---|
| Data jadwal ruangan ada di sistem akademik, tapi status proyektor hanya ada di buku log fisik TI | Tidak ada satu sistem yang tahu semuanya sekaligus |
| Booking dikonfirmasi, tapi baru ketahuan proyektor rusak saat acara sudah mulai | Kekacauan di hari H |
| Chatbot AI biasa bisa mengarang (*halusinasi*): "Iya, ruangan tersedia!" padahal tidak cek database | Data palsu, booking fiktif |
| Proses manual: telfon bagian fasilitas → telfon TI → telfon pemeliharaan | Butuh waktu berhari-hari untuk satu pemesanan |

**CampusFlow hadir untuk menghilangkan semua masalah ini.**

---

## 🎯 Bagian 2 — Apa Itu CampusFlow?

> **CampusFlow** adalah sistem agen AI otonom yang menerima instruksi bahasa alami, lalu menjalankan seluruh proses validasi fasilitas kampus secara otomatis, deterministik, dan aman — sebelum memutuskan apakah sebuah reservasi boleh dibuat.

### Analogi Sederhana

Bayangkan CampusFlow seperti seorang **Manajer Fasilitas Super Efisien** yang:
- Mengerti bahasa manusia biasa ("Pesan ruang untuk workshop AI 100 orang Selasa depan")
- Langsung cek ketersediaan ruangan di database
- Langsung verifikasi kapasitas secara matematis (bukan tebak-tebakan)
- Langsung baca log pemeliharaan untuk memastikan proyektor tidak rusak
- **Hanya** membuat reservasi jika semua syarat terpenuhi 100%
- Langsung kirim notifikasi ke departemen yang tepat

### Perbedaan Utama dari Chatbot Biasa

```
Chatbot Biasa:
  User → "Pesan ruangan besok"
  AI   → "Baik, ruangan sudah dipesan! ✅"  (padahal tidak cek database sama sekali)

CampusFlow:
  User   → "Pesan ruangan besok"
  System → Cek ketersediaan via Database MCP
  System → Cek kapasitas via Database MCP
  System → Baca log pemeliharaan via Filesystem MCP
  System → Jika semua lulus: tulis reservasi ke database (ACID transaction)
  System → Kirim notifikasi ke departemen via Notification MCP
  AI     → "Reservasi BK-2026-015 berhasil dibuat. Auditorium Utama, Selasa 2026-10-06, 09:00–11:00. Notifikasi terkirim ke Tim Fasilitas Akademik." ✅
```

---

## ⚙️ Bagian 3 — Teknologi yang Digunakan dan Fungsinya

CampusFlow dibangun dengan tumpukan teknologi yang sangat spesifik dan saling melengkapi.

### 3.1 Stack Inti

| Teknologi | Versi | Fungsi dalam CampusFlow |
|---|---|---|
| **Python** | 3.14.0 | Bahasa utama untuk seluruh sistem |
| **LangGraph** | Latest | Mesin orkestrasi agen — membangun alur kerja sebagai *state machine* eksplisit (graf simpul dan transisi) |
| **MCP SDK Python** | ≥2.2.0 | Protocol resmi untuk menghubungkan agen dengan sumber data eksternal via JSON-RPC 2.0 |
| **Pydantic v2** | ≥2.7.4 | Validasi dan parsing data terstruktur — memastikan setiap entitas (nama ruangan, tanggal, kapasitas) memiliki tipe dan format yang benar |
| **SQLite 3** | Bawaan Python | Database ringan, tidak perlu server terpisah, mendukung transaksi ACID penuh |
| **pytest + pytest-asyncio** | Latest | Framework pengujian untuk 10 skenario wajib |
| **Node.js** | v24.11.1 | Runtime untuk komponen JavaScript pendukung |

### 3.2 Tiga Komponen MCP (Ini adalah Jantung Sistem)

> **MCP (Model Context Protocol)** adalah standar terbuka dari Anthropic yang memungkinkan AI agent berkomunikasi dengan sumber data eksternal secara modular, aman, dan terisolasi.

Setiap server MCP berjalan sebagai **proses Python terpisah** dan berkomunikasi hanya melalui **stdin/stdout** (tidak ada jaringan terbuka, tidak ada HTTP socket).

```
AI Agent (LangGraph)
    │
    ├── stdio (JSON-RPC 2.0) ──→ campusflow-db       ──→ campusflow.db (SQLite)
    │
    ├── stdio (JSON-RPC 2.0) ──→ campusflow-fs        ──→ data/filesystem/*.txt
    │
    └── stdio (JSON-RPC 2.0) ──→ campusflow-notification ──→ Notification Store
```

#### Server MCP 1: `campusflow-db` (Database)
**Fungsi:** Pintu masuk terkontrol ke database SQLite

| Tool | Fungsi |
|---|---|
| `inspect_schema` | Melihat struktur tabel database |
| `query_room_availability` | Cek apakah ruangan bebas pada jam tertentu |
| `query_room_capacity` | Mendapatkan kapasitas maksimal ruangan |
| `check_booking_conflicts` | Mendeteksi tumpang tindih jadwal |
| `query_equipment` | Mencari peralatan yang terpasang di ruangan |
| `create_booking_transactional` | **Satu-satunya cara membuat reservasi** (via BEGIN IMMEDIATE TRANSACTION) |

> ⚠️ **Prinsip Keamanan:** Server ini hanya menerima kueri SQL berparameter (tidak ada raw SQL injection). Agen tidak bisa menjalankan SQL sembarangan.

#### Server MCP 2: `campusflow-fs` (Filesystem)
**Fungsi:** Akses baca-saja ke file operasional kampus

| Tool | Fungsi |
|---|---|
| `read_file` | Membaca konten file tertentu |
| `search_maintenance_log` | Mencari catatan perbaikan peralatan berdasarkan kode alat |
| `get_equipment_status` | Mendapatkan status terkini peralatan dari file log |

> ⚠️ **Prinsip Keamanan:** Hanya bisa membaca folder `data/filesystem/`. Tidak bisa membaca file sistem Windows atau folder proyek lain (*path traversal guard*).

#### Server MCP 3: `campusflow-notification` (Mock Notification API)
**Fungsi:** Simulasi sistem pesan internal kampus

| Tool | Fungsi |
|---|---|
| `send_department_notification` | Mengirim notifikasi ke departemen target |
| `get_notification_status` | Mengecek status pengiriman notifikasi |
| `list_department_notifications` | Menampilkan riwayat notifikasi departemen |

**Tabel Perutean Notifikasi (Deterministik, bukan tebakan LLM):**

| Kondisi | Departemen Penerima |
|---|---|
| Reservasi berhasil dibuat | `Academic Facilities` |
| Ada masalah/kebutuhan peralatan | `IT & Equipment Support` |
| Kerusakan fisik fasilitas | `Facilities / Maintenance` |
| Bentrok jadwal atau koordinasi khusus | `Event & Academic Affairs` |

---

## 🔄 Bagian 4 — Alur Kerja Lengkap (Step by Step)

Ini adalah inti dari sistem. Setiap permintaan pengguna melewati 9 tahap berurutan. **Tidak boleh ada tahap yang dilewati.**

```
Pengguna mengetik: "Pesan auditorium untuk workshop AI 100 orang Selasa depan jam 9-11"
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TAHAP 1: REQUEST_RECEIVED                                          │
│  → Sistem menerima teks mentah                                      │
│  → Membuat Trace ID unik (UUID) untuk sesi ini                      │
│  → Mencatat waktu mulai di audit log                                │
└─────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TAHAP 2: REQUEST_PARSED                                            │
│  → NLU Parser (LLM atau Deterministic Fallback) mengekstrak entitas:│
│    • Ruangan: "Auditorium Utama"                                    │
│    • Tanggal: "Selasa depan" → 2026-10-06 (tanggal absolut)         │
│    • Jam mulai: 09:00, Jam selesai: 11:00                           │
│    • Kapasitas: 100 orang                                           │
│    • Peralatan: Proyektor                                           │
│  → Jika ada field wajib yang tidak bisa diekstrak → BERHENTI       │
│    Status: INVALID_REQUEST                                          │
└─────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TAHAP 3: ROOM_AVAILABILITY_CHECK (via campusflow-db MCP)           │
│  → Tool: query_room_availability("AUD-01", "2026-10-06", "09:00",  │
│          "11:00")                                                   │
│  → Jika ada booking lain yang tumpang tindih → BERHENTI             │
│    Status: ROOM_UNAVAILABLE                                         │
└─────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TAHAP 4: CAPACITY_VALIDATION (via campusflow-db MCP)               │
│  → Tool: query_room_capacity("AUD-01")                              │
│  → Kapasitas AUD-01 = 200. Peserta = 100. 100 ≤ 200 → LULUS ✅     │
│  → Jika peserta > kapasitas → BERHENTI                              │
│    Status: INSUFFICIENT_CAPACITY                                    │
└─────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TAHAP 5: EQUIPMENT_CHECK (via campusflow-db MCP)                   │
│  → Tool: query_equipment("AUD-01", "projector")                     │
│  → Proyektor PRJ-01 terdaftar di AUD-01 → ADA ✅                   │
│  → Jika alat tidak terdaftar di ruangan → BERHENTI                 │
│    Status: EQUIPMENT_UNAVAILABLE                                    │
└─────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TAHAP 6: EQUIPMENT_STATUS_CHECK (via campusflow-fs MCP)            │
│  → Tool: search_maintenance_log("PRJ-01")                           │
│  → Baca maintenance_logs.txt: "PRJ-01 inspected 2026-09-30.        │
│     Status: OPERATIONAL. No active faults."                         │
│  → LULUS ✅                                                         │
│                                                                     │
│  → Jika status FAULTY/UNDER_MAINTENANCE → BERHENTI                  │
│    Status: EQUIPMENT_UNAVAILABLE                                    │
│  → Jika data tidak ditemukan → BERHENTI                             │
│    Status: EQUIPMENT_STATUS_UNKNOWN                                 │
│  → Jika DB bilang "ACTIVE" tapi log bilang "RUSAK" → BERHENTI      │
│    Status: WORKFLOW_ABORTED (kontradiksi bukti)                     │
└─────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TAHAP 7: BOOKING_WRITE (via campusflow-db MCP)                     │
│  → Tool: create_booking_transactional(...)                          │
│  → BEGIN IMMEDIATE TRANSACTION                                      │
│  → INSERT INTO bookings (room_id, user_id, event_name, ...)         │
│  → COMMIT                                                           │
│  → booking_reference = "BK-2026-015" dibuat ✅                     │
│  → Jika transaksi gagal → BERHENTI                                  │
│    Status: DATABASE_ERROR (tidak pernah lapor "sukses" jika gagal)  │
└─────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TAHAP 8: NOTIFICATION (via campusflow-notification MCP)            │
│  → Tool: send_department_notification("Academic Facilities",        │
│          "Reservasi AUD-01 dikonfirmasi: Workshop AI, 100 orang,   │
│          2026-10-06 09:00-11:00. Proyektor PRJ-01 terverifikasi.") │
│  → Notifikasi terkirim ✅                                           │
│  → Jika notifikasi GAGAL (tapi booking sudah tersimpan):           │
│    Status: COMPLETED_PARTIAL (booking valid, notifikasi gagal)      │
└─────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TAHAP 9: COMPLETED                                                 │
│  → Sistem merespons pengguna dengan konfirmasi lengkap              │
│  → Audit trail tersimpan di tabel audit_logs                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Bagian 5 — Struktur Database (Apa yang Disimpan)

Database menggunakan SQLite dengan 6 tabel utama:

```
buildings (gedung kampus)
    └── rooms (ruangan dalam gedung)
            ├── room_equipment (peralatan yang dipasang di ruangan)
            │       └── equipment (katalog semua peralatan)
            └── bookings (reservasi yang dibuat)
                    └── audit_logs (rekam jejak setiap langkah eksekusi)
```

**Data yang sudah ada dalam database (Seed Data untuk Pengujian):**
- **3 Gedung:** Gedung Utama (MAIN), Gedung Sains (SCI), Gedung Teknik (ENG)
- **8 Ruangan:** Auditorium Utama (200 orang), Ruang Seminar B (50 orang), Lab Komputer, dll.
- **10 Peralatan:** PRJ-01 (proyektor baik), PRJ-02 (proyektor RUSAK), MIC-01, SND-01, dll.
- **5 Booking Awal:** Termasuk skenario bentrok jadwal untuk pengujian
- **6 Pengguna:** Dosen, staf, mahasiswa, admin

---

## 🛡️ Bagian 6 — Aturan Keamanan (Non-Negotiable Rules)

Ini adalah aturan yang **tidak boleh dilanggar dalam kondisi apapun:**

### Aturan 1: Tidak Ada Penulisan Sebelum Validasi Selesai
```
❌ DILARANG: Parse → Tulis ke DB → Validasi
✅ WAJIB:    Parse → Validasi Lengkap → Tulis ke DB → Notifikasi
```

### Aturan 2: LLM Hanya untuk Bahasa, Bukan Logika Bisnis
```
LLM BOLEH melakukan:
  ✅ Memahami "Selasa depan" = 2026-10-06
  ✅ Mengekstrak "100 orang" dari teks natural
  ✅ Menyusun kalimat penjelasan untuk pengguna

LLM DILARANG melakukan:
  ❌ Memutuskan apakah ruangan tersedia (harus dari query DB)
  ❌ Menebak apakah proyektor berfungsi (harus dari file log)
  ❌ Menghitung apakah 150 > kapasitas 100 (harus kode deterministik)
```

### Aturan 3: Status UNKNOWN ≠ AVAILABLE
```
Jika status peralatan tidak bisa diverifikasi:
  UNKNOWN → Tolak booking (bukan: asumsikan baik-baik saja)
```

### Aturan 4: Penanganan Kontradiksi
```
Jika database bilang: PRJ-01 status = "ACTIVE"
TAPI log filesystem bilang: PRJ-01 "currently under repair since Oct 1"

→ STOP semua operasi
→ Laporkan kontradiksi ke pengguna
→ Jangan buat booking dalam kondisi bukti tidak konsisten
```

---

## 📋 Bagian 7 — Persona Pengguna (Siapa yang Menggunakan Sistem)

| Siapa | Peran | Apa yang Mereka Dapat |
|---|---|---|
| **Dosen / Penyelenggara Acara** | Pemohon | Satu perintah bahasa alami = seluruh proses terautomasi |
| **Tim Fasilitas Akademik** | Pengelola Ruangan | Menerima notifikasi reservasi terstruktur, tidak ada double-booking |
| **Tim TI & Multimedia** | Pengelola Peralatan | Sistem tidak pernah memesan alat yang sedang rusak |
| **Tim Pemeliharaan** | Teknisi | Log perbaikan terintegrasi langsung ke sistem validasi |

---

## 📐 Bagian 8 — Rencana Pembangunan (9 Fase)

| Fase | Status | Deskripsi | Hasil Keluaran |
|---|---|---|---|
| **Fase 0** | ✅ SELESAI | Inisialisasi proyek, audit lingkungan | `PROJECT_CONTEXT.md` |
| **Fase 1** | ✅ SELESAI | Riset & brainstorming teknis | `docs/research.md`, `problem-definition.md`, `architecture-decisions.md` |
| **Fase 2** | ✅ SELESAI | Desain sistem arsitektur | `docs/architecture.md`, `workflow.md`, `state-machine.md`, `data-model.md`, `mcp-architecture.md` |
| **Fase 3** | ✅ SELESAI | Database & seed data | `schema.sql`, `seed.sql`, `init_db.py`, `campusflow.db` |
| **Fase 4** | ⏳ SELANJUTNYA | Implementasi 3 server MCP | `mcp_db_server.py`, `mcp_fs_server.py`, `mcp_notification_server.py` |
| **Fase 5** | 🔜 | Orkestrasi agen LangGraph | Graf alur kerja dengan 10 simpul node |
| **Fase 6** | 🔜 | Guardrails & keamanan | Penegakan invariant, pencegahan halusinasi |
| **Fase 7** | 🔜 | Suite pengujian otomatis | 10 skenario uji (lihat detail di bawah) |
| **Fase 8** | 🔜 | Audit akhir & demonstrasi | Demo, README final, laporan audit |

---

## 🧪 Bagian 9 — 10 Skenario Pengujian Wajib

Ini adalah bukti bahwa sistem benar-benar berfungsi sesuai desain:

| No | Nama Skenario | Input | Hasil yang Diharapkan |
|---|---|---|---|
| 1 | ✅ **Sukses Penuh** | Ruangan tersedia, kapasitas cukup, proyektor baik | `booking=CREATED`, `notification=SENT` |
| 2 | ❌ **Ruangan Tidak Tersedia** | Ruangan sudah dipesan orang lain | `booking=NOT_CREATED`, status=`ROOM_UNAVAILABLE` |
| 3 | ❌ **Kapasitas Kurang** | 200 orang, tapi ruangan hanya muat 50 | `booking=NOT_CREATED`, status=`INSUFFICIENT_CAPACITY` |
| 4 | ❌ **Proyektor Rusak** | Log pemeliharaan: "PRJ-02 FAULTY" | `booking=NOT_CREATED`, status=`EQUIPMENT_UNAVAILABLE` |
| 5 | ❌ **Status Alat Tidak Diketahui** | Tidak ada catatan inspeksi alat | `booking=NOT_CREATED`, status=`EQUIPMENT_STATUS_UNKNOWN` |
| 6 | ❌ **Kegagalan Database** | Simulasi database terkunci (rollback) | `booking=FAILED`, sistem tidak lapor sukses |
| 7 | ⚠️ **Notifikasi Gagal** | Booking berhasil, tapi Mock API notif timeout | `booking=CREATED`, `notification=FAILED` (PARTIAL) |
| 8 | ❌ **Bukti Kontradiktif** | DB bilang alat "ACTIVE", log bilang "RUSAK" | `workflow=ABORTED`, `booking=NOT_CREATED` |
| 9 | ❓ **Permintaan Ambigu** | "Pesan ruangan minggu depan" (tanpa jam/nama) | `workflow=NEEDS_CLARIFICATION` |
| 10 | ❌ **Reservasi Duplikat** | Booking yang persis sama dikirim dua kali | Booking kedua `REJECTED` (idempotency) |

---

## 🎬 Bagian 10 — Demo Akhir yang Harus Bisa Dijalankan

**Input Utama (Kasus Sukses):**
```
"Book the main auditorium for a 100-person AI workshop next Tuesday, 
 check if the projector is working, and notify the facilities team."
```

**Output yang Terlihat di Terminal:**
```
[01] REQUEST RECEIVED         ← Teks diterima, Trace ID: abc-123-...
[02] REQUEST PARSED           ← Room: AUD-01 | Date: 2026-10-07 | Cap: 100
[03] ROOM AVAILABILITY CHECK  ← AUD-01 pada 2026-10-07 09:00-11:00: AVAILABLE ✅
[04] CAPACITY VALIDATION      ← 100 ≤ 200 (kapasitas AUD-01): PASS ✅
[05] EQUIPMENT CHECK          ← PRJ-01 terdaftar di AUD-01: FOUND ✅
[06] EQUIPMENT STATUS CHECK   ← PRJ-01 log: OPERATIONAL (inspeksi 2026-09-30) ✅
[07] ALL VALIDATIONS PASSED   ← Semua prasyarat terpenuhi
[08] BOOKING CREATED          ← BK-2026-015 tersimpan di database ✅
[09] NOTIFICATION SENT        ← Academic Facilities diberitahu ✅
[10] WORKFLOW COMPLETED       ← Selesai dalam 1.23 detik
```

**Output untuk Kasus Gagal (Proyektor Rusak):**
```
[01] REQUEST RECEIVED
[02] REQUEST PARSED
[03] ROOM AVAILABILITY CHECK  ← AVAILABLE ✅
[04] CAPACITY VALIDATION      ← PASS ✅
[05] EQUIPMENT CHECK          ← PRJ-02 ditemukan ✅
[06] EQUIPMENT STATUS CHECK   ← PRJ-02 log: FAULTY (sedang diperbaiki sejak 2026-10-01) ❌
[07] BOOKING NOT CREATED      ← Proyektor tidak laik pakai
[--] Alur kerja BERHENTI di sini, tidak ada penulisan ke database
```

---

## 🗂️ Bagian 11 — Struktur File Proyek

```
d:\TalentSource\CampusFlow\
│
├── PROJECT_CONTEXT.md              ← Ringkasan konteks proyek
├── README.md                       ← Dokumentasi publik (dibuat di Fase 8)
│
├── docs/                           ← Dokumentasi desain sistem (Fase 1-2, SELESAI)
│   ├── research.md                 ← Riset dan analisis teknis
│   ├── problem-definition.md       ← Definisi masalah & persona pengguna
│   ├── architecture-decisions.md   ← Keputusan arsitektur & ADR
│   ├── architecture.md             ← Desain arsitektur sistem
│   ├── workflow.md                 ← Alur kerja lengkap (+ diagram Mermaid)
│   ├── state-machine.md            ← Spesifikasi mesin status LangGraph
│   ├── data-model.md               ← Skema database & ERD
│   └── mcp-architecture.md         ← Arsitektur 3 server MCP
│
├── data/
│   ├── database/                   ← Fase 3 (SELESAI)
│   │   ├── schema.sql              ← Definisi tabel & constraint
│   │   ├── seed.sql                ← Data awal (ruangan, alat, booking contoh)
│   │   ├── init_db.py              ← Skrip inisialisasi database
│   │   └── campusflow.db           ← File SQLite aktif
│   │
│   └── filesystem/                 ← Data operasional kampus (Fase 3, SELESAI)
│       ├── maintenance_logs.txt    ← Catatan perbaikan peralatan
│       ├── equipment_inventory.txt ← Inventaris peralatan
│       └── equipment_status.txt    ← Status terkini peralatan
│
├── src/                            ← Kode utama (Fase 4-6, BELUM DIBUAT)
│   ├── mcp/
│   │   ├── mcp_db_server.py        ← Server MCP Database
│   │   ├── mcp_fs_server.py        ← Server MCP Filesystem
│   │   └── mcp_notification_server.py ← Server MCP Notifikasi
│   │
│   ├── agent/
│   │   ├── graph.py                ← Graf LangGraph utama
│   │   ├── state.py                ← Definisi AgentState (Pydantic)
│   │   └── nodes/                  ← Satu file per simpul alur kerja
│   │       ├── parse_request.py
│   │       ├── check_room.py
│   │       ├── validate_capacity.py
│   │       ├── check_equipment.py
│   │       ├── authorize_booking.py
│   │       ├── create_booking.py
│   │       ├── send_notification.py
│   │       └── handle_failure.py
│   │
│   └── nlu/
│       └── parser.py               ← NLU Parser (LLM + Deterministic Fallback)
│
├── tests/                          ← Suite pengujian 10 skenario (Fase 7)
│   ├── test_01_success.py
│   ├── test_02_room_unavailable.py
│   └── ... (dst.)
│
├── .agents/skills/                 ← Custom skills AI agent (TERPASANG)
│   ├── ponytail/
│   ├── mcp-builder/
│   ├── test-driven-development/
│   └── ... (10 skill total)
│
└── prompts/
    └── 00_MASTER_PROMPT.md         ← Spesifikasi teknis utama proyek
```

---

## 📊 Bagian 12 — Ringkasan Status Proyek

```
FASE 0 ████████████████████ 100%  ✅ Inisialisasi Proyek
FASE 1 ████████████████████ 100%  ✅ Riset & Analisis
FASE 2 ████████████████████ 100%  ✅ Desain Sistem
FASE 3 ████████████████████ 100%  ✅ Database & Seed Data
─────────────────────────────────────────────────────
FASE 4 ░░░░░░░░░░░░░░░░░░░░   0%  ⏳ 3 Server MCP  ← KITA ADA DI SINI
FASE 5 ░░░░░░░░░░░░░░░░░░░░   0%  🔜 Orkestrasi LangGraph
FASE 6 ░░░░░░░░░░░░░░░░░░░░   0%  🔜 Guardrails & Keamanan
FASE 7 ░░░░░░░░░░░░░░░░░░░░   0%  🔜 10 Skenario Pengujian
FASE 8 ░░░░░░░░░░░░░░░░░░░░   0%  🔜 Audit & Demo Akhir
```

---

*Dokumen ini dibuat berdasarkan: [PROJECT_CONTEXT.md](file:///d:/TalentSource/CampusFlow/PROJECT_CONTEXT.md), [problem-definition.md](file:///d:/TalentSource/CampusFlow/docs/problem-definition.md), [workflow.md](file:///d:/TalentSource/CampusFlow/docs/workflow.md), [state-machine.md](file:///d:/TalentSource/CampusFlow/docs/state-machine.md), [data-model.md](file:///d:/TalentSource/CampusFlow/docs/data-model.md), [mcp-architecture.md](file:///d:/TalentSource/CampusFlow/docs/mcp-architecture.md), dan [00_MASTER_PROMPT.md](file:///d:/TalentSource/CampusFlow/prompts/00_MASTER_PROMPT.md)*
