# Alur Kerja Sistem: CampusFlow
**Workflow Pemrosesan Permintaan Pemesanan Fasilitas Kampus**

Dokumen ini mendeskripsikan alur kerja lengkap dari momen pengguna mengirim instruksi bahasa alami hingga sistem menghasilkan respons akhir—baik berupa konfirmasi pemesanan sukses maupun laporan kegagalan yang terstruktur.

---

## 1. Peta Alur Kerja Keseluruhan

```mermaid
flowchart TD
    START(["🧑 Pengguna Mengirim Permintaan\n(Bahasa Alami)"])

    P1["📥 REQUEST_RECEIVED\nTerima & catat permintaan mentah"]
    P2["🔍 REQUEST_PARSED\nExtraksi entitas:\nruangan, tanggal, jam, kapasitas,\nalat, pemohon"]

    CHK_PARSE{{"Apakah semua field\nwajib lengkap?"}}

    P3["✅ REQUIREMENTS_VALIDATED\nResolusi tanggal relatif\nke tanggal absolut"]
    P4["🏢 ROOM_SEARCH\nQuery daftar ruangan\nyang sesuai dari DB"]
    P5["📅 ROOM_AVAILABILITY_CHECK\nPeriksa bentrok jadwal\ndi database"]

    CHK_ROOM{{"Ruangan\ntersedia?"}}

    P6["👥 CAPACITY_VALIDATION\nBandingkan jumlah peserta\ndengan kapasitas ruangan"]

    CHK_CAP{{"Kapasitas\ncukup?"}}

    P7["🔌 EQUIPMENT_CHECK\nQuery peralatan wajib\ndi database"]

    CHK_EQUIP_EXIST{{"Alat\nada?"}}

    P8["🛠️ EQUIPMENT_STATUS_CHECK\nVerifikasi status fisik alat\nvia Filesystem MCP\n(maintenance log)"]

    CHK_EQUIP_STATUS{{"Status alat\noperasional?"}}

    CHK_CONFLICT{{"Ada\nkontradiksi\nbukti?"}}

    P9["🔐 BOOKING_AUTHORIZATION\nSemua validasi lulus\nSiapkan data transaksi"]
    P10["💾 BOOKING_WRITE\nTulis reservasi ke SQLite\n(BEGIN IMMEDIATE TRANSACTION)"]

    CHK_DB{{"Transaksi\nberhasil?"}}

    P11["📢 NOTIFICATION\nKirim notifikasi\nke departemen terkait"]

    CHK_NOTIF{{"Notifikasi\nterkirim?"}}

    F_DONE(["✅ COMPLETED\nReservasi Terkonfirmasi\nNotifikasi Terkirim"])
    F_PARTIAL(["⚠️ COMPLETED_PARTIAL\nReservasi Terkonfirmasi\nNotifikasi GAGAL"])

    FAIL_INVALID(["❌ INVALID_REQUEST\nData tidak lengkap /\nAmbigu — Minta klarifikasi"])
    FAIL_ROOM(["❌ ROOM_UNAVAILABLE\nRuangan bentrok\nSarankan alternatif"])
    FAIL_CAP(["❌ INSUFFICIENT_CAPACITY\nKapasitas tidak cukup\nSarankan ruangan lebih besar"])
    FAIL_EQUIP(["❌ EQUIPMENT_UNAVAILABLE\nAlat tidak ada /\nAlat rusak"])
    FAIL_STATUS(["❌ EQUIPMENT_STATUS_UNKNOWN\nStatus alat tidak\ndapat diverifikasi"])
    FAIL_CONFLICT(["❌ WORKFLOW_ABORTED\nBukti kontradiktif\nHentikan semua proses"])
    FAIL_DB(["❌ DATABASE_ERROR\nTransaksi gagal\nJangan laporkan sukses"])

    START --> P1 --> P2 --> CHK_PARSE
    CHK_PARSE -- "❌ Tidak Lengkap" --> FAIL_INVALID
    CHK_PARSE -- "✅ Lengkap" --> P3 --> P4 --> P5 --> CHK_ROOM
    CHK_ROOM -- "❌ Bentrok" --> FAIL_ROOM
    CHK_ROOM -- "✅ Tersedia" --> P6 --> CHK_CAP
    CHK_CAP -- "❌ Tidak Cukup" --> FAIL_CAP
    CHK_CAP -- "✅ Cukup" --> P7 --> CHK_EQUIP_EXIST
    CHK_EQUIP_EXIST -- "❌ Tidak Ada" --> FAIL_EQUIP
    CHK_EQUIP_EXIST -- "✅ Ada" --> P8 --> CHK_CONFLICT
    CHK_CONFLICT -- "⚠️ Kontradiksi" --> FAIL_CONFLICT
    CHK_CONFLICT -- "✅ Konsisten" --> CHK_EQUIP_STATUS
    CHK_EQUIP_STATUS -- "❌ Rusak/Unknown" --> FAIL_EQUIP
    CHK_EQUIP_STATUS -- "✅ Operasional" --> P9 --> P10 --> CHK_DB
    CHK_DB -- "❌ Gagal" --> FAIL_DB
    CHK_DB -- "✅ Berhasil" --> P11 --> CHK_NOTIF
    CHK_NOTIF -- "✅ Terkirim" --> F_DONE
    CHK_NOTIF -- "❌ Gagal" --> F_PARTIAL
```

---

## 2. Deskripsi Detail Setiap Tahapan

### Tahap 1 — REQUEST_RECEIVED
- **Apa yang terjadi:** Sistem menerima teks permintaan mentah dari pengguna dan membuat entri jejak audit baru dengan UUID unik untuk sesi ini.
- **Alat yang digunakan:** Tidak ada (operasi internal).
- **Perubahan State:** `request_raw` diisi, `trace_id` dibuat, `workflow_status` ← `REQUEST_RECEIVED`.

---

### Tahap 2 — REQUEST_PARSED
- **Apa yang terjadi:** NLU Parser mengekstrak entitas-entitas penting dari teks permintaan.
  - Nama ruangan / jenis ruangan.
  - Nama acara dan pemohon.
  - Tanggal (termasuk resolusi waktu relatif: "Selasa depan" → `2026-09-22`).
  - Jam mulai dan jam selesai.
  - Jumlah peserta.
  - Jenis peralatan yang dibutuhkan.
  - Departemen yang harus diberitahu.
- **Aturan:** Jika salah satu field wajib tidak dapat diekstrak dengan kepastian, sistem wajib berhenti dan melaporkan status `INVALID_REQUEST` beserta daftar informasi yang kurang.
- **Alat yang digunakan:** NLU Parser (LLM atau Deterministic Fallback).
- **Perubahan State:** `parsed_request` (BookingRequest Pydantic) diisi.

---

### Tahap 3 — REQUIREMENTS_VALIDATED
- **Apa yang terjadi:** Sistem memvalidasi format seluruh entitas yang sudah diekstrak:
  - Tanggal dikonversi ke format ISO 8601 (`YYYY-MM-DD`).
  - Waktu divalidasi dalam format `HH:MM` dengan jam operasional valid (07:00–22:00).
  - Jumlah peserta adalah bilangan bulat positif.
- **Alat yang digunakan:** Logika program deterministik (tidak menggunakan LLM atau MCP).
- **Perubahan State:** `requirements_validated` ← `True`.

---

### Tahap 4 — ROOM_SEARCH
- **Apa yang terjadi:** Sistem meminta daftar ruangan yang cocok dari database berdasarkan nama atau tipe yang disebutkan pengguna.
- **Alat yang digunakan:** `campusflow-db` → `inspect_schema()` + `query_room_capacity()`.
- **Perubahan State:** `candidate_rooms` diisi dengan daftar opsi ruangan yang memenuhi filter.

---

### Tahap 5 — ROOM_AVAILABILITY_CHECK
- **Apa yang terjadi:** Sistem memeriksa apakah ruangan yang diminta tidak memiliki bentrok reservasi di database untuk rentang tanggal dan jam yang diminta.
- **Logika Pendeteksian Bentrok:**
  - Ruangan dianggap **TERSEDIA** jika tidak ada reservasi aktif dengan kondisi: `existing.start_time < requested.end_time AND existing.end_time > requested.start_time`.
- **Alat yang digunakan:** `campusflow-db` → `check_booking_conflicts()`.
- **Perubahan State:** `room_availability` ← `{status: "AVAILABLE" | "UNAVAILABLE", conflicts: [...]}`.

---

### Tahap 6 — CAPACITY_VALIDATION
- **Apa yang terjadi:** Sistem mengambil kapasitas maksimum ruangan dari database dan membandingkannya dengan jumlah peserta yang diminta.
- **Logika:** `attendee_count <= room.capacity` → Lulus; sebaliknya → Gagal.
- **Alat yang digunakan:** `campusflow-db` → `query_room_capacity()`.
- **Perubahan State:** `capacity_validation` ← `{status: "PASS" | "FAIL", room_capacity: N, requested: M}`.

---

### Tahap 7 — EQUIPMENT_CHECK
- **Apa yang terjadi:** Sistem mengambil data peralatan yang terdaftar di ruangan tersebut dari database dan memverifikasi apakah jenis alat yang dibutuhkan tersedia di sana.
- **Alat yang digunakan:** `campusflow-db` → `query_equipment()`.
- **Perubahan State:** `equipment_results` ← `{equipment_id, db_status, equipment_type}`.

---

### Tahap 8 — EQUIPMENT_STATUS_CHECK
- **Apa yang terjadi:** Sistem membaca catatan pemeliharaan dan status fisik alat dari file teks operasional kampus di folder `data/filesystem/`. Ini adalah lapisan verifikasi bukti independen terpisah dari database.
- **Penanganan Kontradiksi:** Jika database menyatakan `"ACTIVE"` namun catatan log menyatakan `"UNDER_MAINTENANCE"` atau `"FAULTY"`, sistem mendeteksi kontradiksi dan melaporkan `WORKFLOW_ABORTED`.
- **Klasifikasi Status:**
  - `OPERATIONAL` → Lulus.
  - `UNDER_MAINTENANCE` / `FAULTY` → `EQUIPMENT_UNAVAILABLE`.
  - `UNKNOWN` / Data tidak ditemukan → `EQUIPMENT_STATUS_UNKNOWN` → Gagal.
- **Alat yang digunakan:** `campusflow-fs` → `get_equipment_status()`, `search_maintenance_log()`.
- **Perubahan State:** `equipment_status` ← `{status: "OPERATIONAL" | "UNDER_MAINTENANCE" | "FAULTY" | "UNKNOWN" | "CONFLICT"}`.

---

### Tahap 9 — BOOKING_AUTHORIZATION
- **Apa yang terjadi:** Sistem melakukan pemeriksaan akhir atas seluruh hasil validasi dalam `Agent State`. Jika dan hanya jika semua validasi bernilai `PASS`, sistem mengotorisasi eksekusi transaksi pembuatan reservasi.
- **Alat yang digunakan:** Logika program deterministik.
- **Perubahan State:** `booking_authorized` ← `True`.

---

### Tahap 10 — BOOKING_WRITE
- **Apa yang terjadi:** Sistem melakukan penulisan data reservasi ke database SQLite dalam satu transaksi atomik terisolasi (`BEGIN IMMEDIATE ... COMMIT`). Jika dalam rentang waktu transaksi berlangsung ada reservasi lain yang bertabrakan (race condition), basis data akan menolak secara otomatis.
- **Alat yang digunakan:** `campusflow-db` → `create_booking_transactional()`.
- **Perubahan State:** `booking_id` diisi jika sukses; `errors` diisi jika transaksi gagal.

---

### Tahap 11 — NOTIFICATION
- **Apa yang terjadi:** Sistem mengirim notifikasi terstruktur ke departemen kampus yang sesuai melalui Mock API Notifikasi.
- **Payload notifikasi mencakup:** ID reservasi, nama ruangan, nama acara, waktu pelaksanaan, jumlah peserta, nama pemohon, dan status alat.
- **Penanganan Kegagalan Parsial:** Jika pengiriman notifikasi gagal setelah reservasi tercatat sah, status akhir workflow adalah `COMPLETED_PARTIAL` — bukan rollback.
- **Alat yang digunakan:** `campusflow-notification` → `send_department_notification()`.
- **Perubahan State:** `notification_status` ← `"SENT"` atau `"FAILED"`.

---

## 3. Alur Kegagalan (*Failure Paths Summary*)

| Status Kegagalan | Penyebab | Yang TIDAK Terjadi |
|---|---|---|
| `INVALID_REQUEST` | Data permintaan tidak lengkap / ambigu | Tidak ada kueri ke DB atau MCP apapun |
| `ROOM_UNAVAILABLE` | Bentrok jadwal dengan reservasi yang sudah ada | Tidak ada pembuatan reservasi baru |
| `INSUFFICIENT_CAPACITY` | Kapasitas ruangan < jumlah peserta | Tidak ada pembuatan reservasi baru |
| `EQUIPMENT_UNAVAILABLE` | Alat tidak ada / rusak / dalam perbaikan | Tidak ada pembuatan reservasi baru |
| `EQUIPMENT_STATUS_UNKNOWN` | Status fisik alat tidak dapat diverifikasi | Tidak ada pembuatan reservasi baru |
| `WORKFLOW_ABORTED` | Bukti database vs. filesystem saling bertentangan | Tidak ada pembuatan reservasi baru |
| `DATABASE_ERROR` | Kegagalan teknis saat transaksi DB | Tidak ada laporan sukses palsu |
| `NOTIFICATION_ERROR` | API notifikasi gagal setelah reservasi sukses | **Reservasi TIDAK dibatalkan** |
