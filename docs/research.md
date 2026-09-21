# Riset Mendalam & Analisis Teknis: CampusFlow
**Sistem Orkestrasi Agen Fasilitas & Acara Kampus Akademik**

Dokumen ini memuat analisis mendalam terhadap 10 pilar utama arsitektur CampusFlow untuk memastikan sistem dibangun di atas fondasi rekayasa perangkat lunak yang andal, deterministik, dan aman.

---

## 1. Alur Kerja Pemesanan Fasilitas Kampus (*Campus Facility Booking Workflow*)

### Fakta Terdokumentasi
- Di lingkungan akademik universitas, pemesanan fasilitas (seperti aula utama, ruang seminar, laboratorium komputer) bukan sekadar alokasi slot kalender sederhana, melainkan melibatkan validasi bertingkat:
  1. **Validasi Hak Akses & Kapasitas:** Jumlah peserta harus lebih kecil atau sama dengan kapasitas legal ruangan.
  2. **Resolusi Temporal:** Rentang waktu acara (tanggal, jam mulai, jam selesai) tidak boleh tumpang tindih (*overlap*) dengan reservasi aktif yang sudah ada.
  3. **Ketersediaan & Kelaikan Peralatan:** Acara sering kali membutuhkan peralatan khusus (proyektor, *sound system*, mikrofon nirkabel) yang harus berada di ruangan dan dalam status operasional prima.
- Pemesanan yang gagal memverifikasi kondisi fisik peralatan sering kali berujung pada kekacauan acara di hari H (*day-of-event failures*).

### Asumsi
- Pengguna umum (dosen, staf, mahasiswa) mengajukan permohonan menggunakan bahasa alami yang sering kali mencantumkan tanggal relatif (misalnya: "Selasa depan", "besok lusa jam 9 pagi") dan deskripsi implisit (misalnya: "butuh proyektor", "workshop 100 orang").
- Sistem menganggap waktu reservasi standar berdurasi tertentu (misal: 2 jam) jika durasi tidak disebutkan secara eksplisit, atau sistem wajib meminta klarifikasi jika waktu tidak lengkap.

### Keputusan Proyek
- Alur pemesanan diwajibkan melewati pipa validasi sekuensial yang ketat:
  $$\text{Ekstraksi Entitas} \to \text{Resolusi Waktu} \to \text{Cek Ketersediaan Ruang} \to \text{Cek Kapasitas} \to \text{Cek Ketersediaan Alat} \to \text{Verifikasi Fisik Alat} \to \text{Otorisasi Transaksi} \to \text{Penulisan Database} \to \text{Disposisi Notifikasi}$$
- **Aturan Mutlak:** Jika salah satu simpul validasi prasyarat gagal, proses pemesanan langsung dibatalkan (*aborted*), dan sistem memberikan penjelasan kegagalan beserta opsi alternatif (bila ada).

### Pertanyaan Belum Terselesaikan
- *Bagaimana kebijakan batas waktu pemesanan (lead time minimal, misal harus H-2)?* Untuk prototipe ini, pemesanan diizinkan untuk tanggal mendatang apa pun tanpa batasan lead time minimum.

---

## 2. Perutean Sumber Daya Multi-Departemen (*Multi-Departmental Resource Routing*)

### Fakta Terdokumentasi
- Pengelolaan kampus terdistribusi ke berbagai unit independen:
  - **Fasilitas Akademik (*Academic Facilities*):** Menangani izin penggunaan ruangan, kunci akses, tata letak kursi/meja.
  - **Dukungan TI & Multimedia (*IT & Media Services*):** Mengurus proyektor, audio/video, jaringan internet, mikrofon.
  - **Pemeliharaan & Kebersihan (*Facilities & Maintenance*):** Menangani perbaikan fisik, AC, kebersihan pra dan pasca acara.
  - **Biro Acara & Protokoler (*Event & Academic Affairs*):** Koordinasi jadwal publik dan pengawasan perizinan acara besar.

### Asumsi
- Notifikasi ke departemen tidak boleh bergantung pada tebakan bebas LLM, melainkan harus dipetakan berdasarkan tipe sumber daya dan aksi yang diambil.

### Keputusan Proyek
- Menerapkan tabel pemetaan aturan perutean (*deterministic routing table*):
  - Sukses Reservasi Ruang $\to$ Notifikasi ke `Academic Facilities`.
  - Masalah Alat / Permintaan Alat Khusus $\to$ Notifikasi ke `IT/Equipment Support`.
  - Kerusakan Fisik Fasilitas $\to$ Notifikasi ke `Facilities/Maintenance`.
  - Eskalasi Bentrok Jadwal / Koordinasi Khusus $\to$ Notifikasi ke `Event Affairs`.
- Format payload notifikasi distandardisasi dengan skema JSON terstruktur (ID tiket, ruangan, nama acara, waktu, status alat, daftar departemen penerima).

### Pertanyaan Belum Terselesaikan
- *Apakah setiap departemen membutuhkan mekanisme konfirmasi balik (acknowledgment)?* Pada fase ini, protokol transmisi bersifat satu arah (pengiriman + status pengiriman: `SENT` / `FAILED`).

---

## 3. Arsitektur Model Context Protocol (MCP)

### Fakta Terdokumentasi
- Model Context Protocol (MCP) adalah standar terbuka yang diperkenalkan oleh Anthropic untuk menghubungkan model AI dengan data eksternal dan *tools* secara aman dan modular.
- MCP memisahkan agen (klien) dari implementasi sumber data (server) melalui protokol berbasis JSON-RPC 2.0.
- Komunikasi dapat berjalan melalui saluran standar masukan/keluaran (`stdio`) atau Server-Sent Events (SSE).

### Asumsi
- Saluran komunikasi `stdio` adalah yang paling stabil, berkinerja tinggi, dan minim *overhead* jaringan untuk server lokal pada sistem operasi Windows.

### Keputusan Proyek
- Arsitektur CampusFlow mengadopsi 3 server MCP mandiri berbasis `stdio`:
  1. `campusflow-db` (Database SQLite)
  2. `campusflow-fs` (Filesystem Operasional Sandbox)
  3. `campusflow-notification` (Mock API Notifikasi Kampus)
- Digunakan pustaka resmi `mcp` SDK Python (`mcp>=2.2.0`).

### Pertanyaan Belum Terselesaikan
- *Apakah server MCP perlu dijalankan sebagai proses terpisah (subproses) saat pengujian?* Ya, saat pengujian integrasi penuh digunakan klien MCP resmi yang meluncurkan subproses via `stdio`. Untuk pengujian unit cepat, disediakan antarmuka pemanggil langsung (*direct tool interface*).

---

## 4. Batasan Alat MCP (*MCP Tool Boundaries & Least Privilege*)

### Fakta Terdokumentasi
- Memberikan izin eksekusi SQL mentah (*arbitrary SQL*) atau akses *file system* tanpa batas kepada LLM memicu kerentanan kritis: SQL Injection, modifikasi tabel tak berizin, pembacaan file sensitif sistem operasi (*directory traversal*).

### Asumsi
- Agen hanya membutuhkan fungsi-fungsi tingkat tinggi (*domain-specific tools*) yang membungkus logika kueri dan manipulasi data.

### Keputusan Proyek
- Menerapkan prinsip *Least Privilege*:
  - **Database MCP:** Tidak mengekspos `execute_raw_sql`. Hanya mengekspos fungsi terdefinisi:
    - `inspect_schema()`
    - `query_room_availability(room_name, date, start_time, end_time)`
    - `query_room_capacity(room_name)`
    - `check_booking_conflicts(room_name, date, start_time, end_time)`
    - `query_equipment(room_name, equipment_type)`
    - `create_booking_transactional(room_id, event_name, requester, date, start_time, end_time, attendee_count)`
  - **Filesystem MCP:** Dibatasi hanya pada direktori `data/filesystem/`. Tidak menerima absolute path di luar folder sandbox. Menggunakan validasi path aman (`os.path.commonpath`).
  - **Notification MCP:** Menerima payload tervalidasi dengan validasi skema Pydantic.

### Pertanyaan Belum Terselesaikan
- *Tidak ada.* Batasan alat telah didefinisikan secara tegas.

---

## 5. Pola Orkestrasi LangGraph / ReAct (*Orchestration Patterns*)

### Fakta Terdokumentasi
- Model ReAct murni (LLM bebas memilih alat dalam loop `Thought -> Action -> Observation`) rentan terhadap:
  - Loop tak terhingga (*infinite cycling*).
  - Melewatkan langkah validasi wajib (misal: langsung booking tanpa cek alat).
  - Inkonsistensi format penanganan kesalahan.
- LangGraph memungkinkan perancangan alur kerja berbasis graf siklik terarah (*Directed State Graph*) dengan transisi bersyarat (*conditional edges*) yang mengeksekusi logika deterministik pada simpul-simpulnya.

### Asumsi
- Alur kerja pemesanan fasilitas kampus memiliki tahapan linier dengan cabang-cabang kegagalan eksplisit.

### Keputusan Proyek
- Menggunakan `LangGraph` untuk mengelola *State Graph*.
- Setiap simpul graf merepresentasikan tahapan pemrosesan terisolasi:
  `parse_request` $\to$ `validate_requirements` $\to$ `check_room` $\to$ `validate_capacity` $\to$ `check_equipment` $\to$ `authorize_booking` $\to$ `create_booking` $\to$ `send_notification` $\to$ `finalize_workflow`.
- Transisi antar simpul diatur oleh *conditional edges* yang memeriksa `validation_results` dalam *Agent State*. Jika ada validasi yang gagal (`PASS == False`), transisi otomatis diarahkan ke simpul `handle_failure`.

### Pertanyaan Belum Terselesaikan
- *Tidak ada.* Arsitektur graf state telah dipetakan secara tuntas.

---

## 6. Guardrails & Integritas Keamanan Agen (*Agent Safety Guardrails*)

### Fakta Terdokumentasi
- Model bahasa besar memiliki sifat probabilistik dan dapat mengalami halusinasi (*confabulation*), seperti berasumsi proyektor dalam kondisi baik meskipun tidak ada catatan fisiknya.

### Asumsi
- Keamanan sistem akademik menuntut kebenaran mutlak (*ground truth*) berbasis bukti empiris alat.

### Keputusan Proyek
- **Prinsip Bukti Otoritatif (*Authoritative Tool Evidence*):** Agen dilarang menyimpulkan status tanpa bukti alat.
- **Klasifikasi Status Empat Nilai:**
  - `AVAILABLE` (Tersedia dan lulus validasi)
  - `UNAVAILABLE` (Tidak tersedia / bentrok jadwal / alat rusak)
  - `UNKNOWN` (Data tidak ditemukan atau tidak dapat diverifikasi)
  - `ERROR` (Kesalahan teknis saat menghubungi alat/sumber data)
- **Guardrail Status:** Nilai `UNKNOWN` tidak boleh diubah menjadi `AVAILABLE`. Jika status alat `UNKNOWN`, pemesanan wajib ditolak dengan alasan status tidak dapat diverifikasi.
- **Deteksi Kontradiksi:** Jika catatan database menyatakan alat "Aktif" namun catatan pemeliharaan filesystem menyatakan "Rusak/Servis", sistem menandai bukti sebagai *kontradiktif/ambigu* dan membatalkan pemesanan demi kehati-hatian (*fail-safe*).

### Pertanyaan Belum Terselesaikan
- *Tidak ada.*

---

## 7. Sistem Pemesanan Transaksional (*Transactional Booking & Concurrency*)

### Fakta Terdokumentasi
- Dua permintaan pemesanan simultan untuk ruangan dan jam yang sama dapat menyebabkan bentrok ganda (*double booking / race condition*) jika pemeriksaan ketersediaan dan penulisan terpisah tanpa isolasi transaksi.

### Asumsi
- SQLite mendukung transaksi ACID penuh. Dengan mode WAL (*Write-Ahead Logging*), pembacaan dan penulisan dapat berlangsung dengan persaingan rendah.

### Keputusan Proyek
- Mengaktifkan `PRAGMA journal_mode=WAL;` dan `PRAGMA foreign_keys=ON;`.
- Operasi pembuatan reservasi dibungkus dalam blok transaksi atomik menggunakan kueri bersyarat berisolasi:
  ```sql
  BEGIN IMMEDIATE TRANSACTION;
  -- Cek bentrok tepat di dalam transaksi yang sama
  -- Tulis data pemesanan jika tidak ada bentrok
  COMMIT;
  ```
- Menambahkan batasan unik (*unique constraint*) atau indeks komposit pada `(room_id, booking_date, start_time, end_time)` untuk memastikan basis data sendiri menolak duplikasi secara permanen di tingkat fisik penyimpanan.

### Pertanyaan Belum Terselesaikan
- *Tidak ada.*

---

## 8. Penanganan Kegagalan Parsial & Kasus Tepi (*Failure Handling*)

### Fakta Terdokumentasi
- Kegagalan dapat terjadi pada berbagai titik:
  - Ruangan penuh / bentrok.
  - Kapasitas tidak mencukupi.
  - Alat rusak atau dalam perbaikan.
  - Server MCP tidak merespons (*timeout*).
  - Basis data galat (*locked* atau I/O error).
  - API notifikasi gagal setelah reservasi berhasil dibuat.

### Asumsi
- Jika reservasi sudah tercatat sah di database, kegagalan pengiriman notifikasi tidak boleh membatalkan (*rollback*) reservasi, melainkan harus dilaporkan sebagai status *partial success*.

### Keputusan Proyek
- Menerapkan pemisahan status hasil akhir:
  - Kasus Normal: `Booking: SUCCESS`, `Notification: SENT`.
  - Kasus Kegagalan Notifikasi: `Booking: SUCCESS`, `Notification: FAILED` (Pesan peringatan: "Reservasi ruangan berhasil dikonfirmasi dengan ID #X, namun notifikasi gagal dikirim ke Departemen Fasilitas").
  - Kasus Validasi Gagal: `Booking: NOT_CREATED`, `Reason: <Rincian Kegagalan>`.

### Pertanyaan Belum Terselesaikan
- *Tidak ada.*

---

## 9. Jejak Audit & Observabilitas (*Audit Logging & Traceability*)

### Fakta Terdokumentasi
- Agen otonom sulit diaudit jika alur penalarannya tersembunyi di dalam *chain-of-thought* internal yang buram.

### Asumsi
- Administrator kampus dan pengembang membutuhkan catatan kronologis yang jelas mengenai apa yang diketahui agen, alat mana yang dipanggil, apa hasilnya, dan mengapa keputusan diambil.

### Keputusan Proyek
- Membangun struktur `ExecutionTrace`:
  - `trace_id` (UUID unik per sesi alur kerja).
  - `timestamp` (Waktu presisi mikrodetik).
  - `step_name` (Nama simpul yang dieksekusi).
  - `evidence` (Data hasil observasi dari alat MCP).
  - `decision` (Keputusan perpindahan status).
- Jejak audit disimpan di dalam *Agent State* dan dicatat ke dalam tabel database `audit_logs` serta file log terstruktur (`campusflow.log`).

### Pertanyaan Belum Terselesaikan
- *Tidak ada.*

---

## 10. Strategi Pengujian Alur Kerja Agen (*Testing Strategies*)

### Fakta Terdokumentasi
- Pengujian agen berbasis LLM sering rapuh (*flaky*) jika bergantung pada model awan non-deterministik dan latensi jaringan.

### Asumsi
- Seluruh logika bisnis dan 10 skenario uji acuan (*Test 1 s/d Test 10*) harus dapat diuji secara otomatis, cepat, deterministik, dan tanpa biaya API.

### Keputusan Proyek
- Membangun piramida pengujian lengkap:
  1. **Unit Test:** Skema data Pydantic, kueri database SQLite, isolasi transaksi, alat filesystem sandbox.
  2. **MCP Integration Test:** Uji komunikasi JSON-RPC klien-server MCP via `stdio`.
  3. **State Machine Test:** Uji setiap transisi graf LangGraph dengan mock evidence.
  4. **End-to-End Test Suite:** Menguji ke-10 skenario wajib dari `00_MASTER_PROMPT.md`:
     - *Test 1:* Pemesanan Sukses (Ruangan + Kapasitas + Proyektor OK).
     - *Test 2:* Ruangan Tidak Tersedia / Bentrok.
     - *Test 3:* Kapasitas Ruangan Tidak Cukup.
     - *Test 4:* Proyektor Rusak / Tidak Tersedia.
     - *Test 5:* Status Proyektor Tidak Diketahui (*Unknown*).
     - *Test 6:* Kesalahan Basis Data.
     - *Test 7:* Kegagalan API Notifikasi (Booking Sukses, Notif Gagal).
     - *Test 8:* Informasi Bertentangan / Kontradiktif.
     - *Test 9:* Permintaan Ambigu / Data Kurang.
     - *Test 10:* Upaya Pemesanan Duplikat Simultan.
- Menggunakan `pytest` dan `pytest-asyncio` sebagai test runner standar.

### Pertanyaan Belum Terselesaikan
- *Tidak ada.*
