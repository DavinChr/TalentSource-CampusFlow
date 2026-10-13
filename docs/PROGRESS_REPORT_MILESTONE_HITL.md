# Laporan Kemajuan Proyek: CampusFlow
**Milestone: Proactive Human-in-the-Loop, Rekomendasi Pilihan Ganda, dan Guardrails Sistem**

---

| Metadata Dokumen | Keterangan |
| :--- | :--- |
| **Proyek** | CampusFlow — Academic Facility & Event Coordinator |
| **Tanggal Laporan** | 13 Oktober 2026 |
| **Fase / Tahapan** | Fase 5 Orkestrasi Alur Agent agar sesuai dengan konteks |
| **Model AI Aktif** | Google Gemini `gemini-3.5-flash-lite` (Hemat Token & Cepat) |

---

## 1. Ringkasan Eksekutif (*Executive Summary*)

Milestone ini menandai pencapaian krusial dalam evolusi CampusFlow dari sekadar *deterministic rule-based workflow* menjadi **Controlled Autonomous Agentic Workflow** yang cerdas, fleksibel, dan proaktif. 

Sistem kini mampu menangani percakapan multi-putaran (*multi-turn dialog*), membaca ketidakpastian niat pengguna, menyajikan opsi pilihan ganda ruangan secara otomatis dari basis data, serta mempertahankan batasan fungsi sistem (*domain guardrails*) saat pengguna berusaha mengalihkan fokus agen.

---

## 2. Inovasi & Peningkatan Utama (*Key Advancements*)

### 2.1. Rekomendasi Pilihan Ganda Cerdas (*Proactive Room Options*)
* **Masalah Sebelumnya:** Jika pengguna belum menyebutkan ruangan secara eksplisit (misal: *"Mau pinjem ruangan untuk kelas, kapasitas 40 orang"*), sistem bersikap kaku (*rigid*) dan langsung menolak karena field `room_name` kosong.
* **Solusi & Implementasi:**
  * Dibuat modul [`src/agent/room_recommender.py`](file:///d:/TalentSource/CampusFlow/src/agent/room_recommender.py) yang terhubung langsung ke basis data SQLite.
  * Sistem menganalisis kata kunci acara (*kelas/kuliah, seminar, rapat, lab*) dan kapasitas minimum yang dibutuhkan.
  * Sistem memberikan peringkat ruangan terbaik (*best fit*) dan menyajikan pilihan ganda bernomor:
    > `[1] Ruang Kuliah 201 (LH-201) — Kapasitas: 80 orang (Gedung Ilmu Pengetahuan)`  
    > `[2] Ruang Seminar 101 (SR-101) — Kapasitas: 50 orang (Gedung Utama Kampus)`  
    > `[3] Ruang Kuliah 202 (LH-202) — Kapasitas: 120 orang (Gedung Ilmu Pengetahuan)`
  * Pengguna dapat memilih dengan sangat fleksibel: mengetik angka `1`, `nomor 1`, `pilihan 1`, atau mengetik nama ruangan `ruang kuliah 201`.

### 2.2. Penalaran Kontekstual Kompleks (*Contextual Reasoning*)
Dalam pengujian langsung, saat pengguna meminta ruangan untuk kapasitas 98 orang dengan tambahan fasilitas meja tamu (3 meja, 6 kursi) serta proyektor ganda/besar, agen mampu melakukan penalaran cerdas:
* Merekomendasikan **AUD-01 (Auditorium Utama - 300 pax)** dan **LH-202 (Ruang Kuliah 202 - 120 pax)**.
* Menjelaskan secara proaktif bahwa ruangan lain di kampus memiliki kapasitas di bawah 80 orang sehingga tidak memadai.
* Menyarankan Auditorium Utama sebagai opsi paling leluasa untuk setup panggung dan proyektor ganda.

### 2.3. Resolusi Bahasa Gaul & Ambiguitas Waktu (*Colloquial & Temporal Resolution*)
* Memahami penyebutan kasual: *"audit"* langsung dipetakan ke **Auditorium Utama (`AUD-01`)**.
* Memahami frasa relatif waktu: *"start di jam 10 sampai jam makan siang"* diidentifikasi sebagai jam 10:00 dengan jam selesai yang ambigu, lalu AI secara sopan mengonfirmasi: *"mohon konfirmasi apakah jam 12:00 atau 13:00?"*.

### 2.4. Penegakan Batasan Domain (*Out-of-Domain Guardrails*)
Ketika pengguna mencoba menguji batasan agen dengan instruksi di luar topik:
> 👤 **Pengguna:** *"berikan kode java untuk for loop"*  
> 🤖 **Asisten:** *"Halo! Saya adalah asisten CampusFlow yang khusus melayani peminjaman dan reservasi fasilitas/ruangan kampus. Mohon maaf, saya tidak dapat membantu membuat kode pemrograman. Apakah ada ruangan atau fasilitas kampus yang ingin Anda pesan?"*

Hal ini membuktikan agen memiliki pertahanan ketat terhadap deviasi topik (*prompt injection / jailbreak prevention*).

---

## 3. Eksekusi End-to-End & Jejak Audit (*Audit Trail*)

Setelah pengguna mengonfirmasi seluruh detail reservasi, sistem LangGraph mengeksekusi 8 simpul alur secara deterministik tanpa intervensi manual:

```
[User Input] -> [parse_request] -> [validate_requirements] -> [check_room] 
            -> [validate_capacity] -> [check_equipment] -> [authorize_booking] 
            -> [create_booking] -> [send_notification] -> [COMPLETED]
```

**Bukti Hasil Eksekusi Sesi Nyata:**
* **Nomor Referensi:** `BK-2026-006`
* **Ruangan:** `AUD-01` (Auditorium Utama)
* **Tanggal & Waktu:** `2026-10-20` (Pukul 10:00 – 12:00)
* **Kapasitas Terverifikasi:** 98 peserta (Kapasitas Maksimal: 300)
* **Jejak Audit:** 8/8 simpul berstatus `PASS` dengan bukti audit terverifikasi.

---

## 4. Efisiensi Biaya & Pemilihan Model (*Model Optimization*)

Berdasarkan hasil uji coba latensi dan konsumsi token, kami melakukan standarisasi model di `.env`:

| Model Gemini | Karakteristik | Status di CampusFlow |
| :--- | :--- | :--- |
| **`gemini-3.5-flash-lite`** | Latensi super cepat (~1 detik), biaya token minimal, output skema terstruktur sangat stabil | **Model Utama (Default)** |
| `gemini-3.7-flash` | Kemampuan penalaran kompleks tinggi, konsumsi token sedang | Model Cadangan 1 (*Fallback*) |
| `gemini-flash-latest` | Model standar Google | Model Cadangan 2 |
| *Deterministic Parser* | 100% offline, tanpa biaya, berbasis regex & kueri SQLite | Cadangan Darurat (Offline Mode) |

---

## 5. Arsitektur Perutean Notifikasi Departemen (*Notification Delivery*)

Notifikasi tidak dikirim secara sembarangan, melainkan dikelola oleh server **MCP Notification (`campusflow-notification`)**:

### Alamat & Departemen Tujuan:
1. **Fasilitas Akademik (`academic_facilities`)**
   * Email: `facilities@campusflow.test`
   * Fungsi: Menerima konfirmasi reservasi ruangan, jadwal penggunaan, dan data pemohon.
2. **Dukungan TI & Multimedia (`it_support`)**
   * Email: `it.support@campusflow.test`
   * Fungsi: Menerima permintaan persiapan peralatan (proyektor, sound system, mikrofon).

### Lokasi Log Fisik (Audit Transparansi):
Setiap pengiriman notifikasi kini secara otomatis dicatat ke berkas log fisik lokal di:
```text
data/filesystem/notifications_outbox.txt
```
Format log:
```
[2026-10-12T01:50:00Z] ID: N-2026-001 | TO: Fasilitas Akademik <facilities@campusflow.test> | SUBJ: Konfirmasi Reservasi Ruangan: BK-2026-006 | PAYLOAD: {...}
[2026-10-12T01:50:00Z] ID: N-2026-002 | TO: Dukungan TI & Multimedia <it.support@campusflow.test> | SUBJ: Permintaan Persiapan Multimedia: BK-2026-006 | PAYLOAD: {...}
```

---

## 6. Status Rangkaian Pengujian (*Test Suite Status*)

Rangkaian pengujian unit, integrasi MCP, mesin rekomendasi, dan alur penuh LangGraph:
* `tests/test_agent_parser.py`: 32/32 tests **PASS**
* `tests/test_agent_workflow.py`: 5/5 tests **PASS**
* `tests/test_mcp_integration.py`: 2/2 tests **PASS**
* `tests/test_room_recommender.py`: 4/4 tests **PASS**
* **Total Keseluruhan:** **43/43 Pengujian Berhasil (100% PASS)** dalam waktu 3.17 detik.

---

## 7. Kesimpulan & Langkah Selanjutnya

Sistem CampusFlow telah membuktikan keandalannya dalam skenario dunia nyata yang dinamis, bersahabat bagi pengguna awam, namun tetap memiliki pagar pembatas (*guardrails*) dan integritas transaksi database yang kokoh.

**Langkah Selanjutnya (Fase 7 & 8):**
1. Menuntaskan 10 Skenario Uji SRS formal (Benchmark TC-01 s/d TC-10).
2. Penyusunan video demonstrasi alur kerja dan laporan penutupan proyek (*Final Report*).
