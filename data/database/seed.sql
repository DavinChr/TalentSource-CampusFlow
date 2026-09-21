-- =============================================================
-- CampusFlow Seed Data
-- Realistic campus data supporting all 10 test scenarios
-- =============================================================

-- ─── BUILDINGS ───────────────────────────────────────────────
INSERT INTO buildings (code, name, address, floors) VALUES
    ('MAIN', 'Gedung Utama Kampus',       'Jl. Kampus Raya No. 1, Lantai 1-4',  4),
    ('SCI',  'Gedung Ilmu Pengetahuan',   'Jl. Kampus Raya No. 2, Sayap Timur', 5),
    ('ENG',  'Gedung Teknik & Rekayasa',  'Jl. Kampus Raya No. 3, Sayap Barat', 3);

-- ─── ROOMS ───────────────────────────────────────────────────
INSERT INTO rooms (building_id, room_code, room_name, room_type, capacity, floor, status) VALUES
    -- Gedung Utama (building_id = 1)
    (1, 'AUD-01',  'Auditorium Utama',        'auditorium',       300, 1, 'ACTIVE'),
    (1, 'SR-101',  'Ruang Seminar 101',        'seminar_room',      50, 1, 'ACTIVE'),
    (1, 'SR-102',  'Ruang Seminar 102',        'seminar_room',      50, 2, 'ACTIVE'),
    (1, 'CR-301',  'Ruang Konferensi Eksekutif','conference_room',  20, 3, 'ACTIVE'),
    -- Gedung Ilmu Pengetahuan (building_id = 2)
    (2, 'LH-201',  'Ruang Kuliah 201',         'lecture_hall',      80, 2, 'ACTIVE'),
    (2, 'LH-202',  'Ruang Kuliah 202',         'lecture_hall',     120, 2, 'ACTIVE'),
    -- Gedung Teknik (building_id = 3)
    (3, 'LAB-401', 'Laboratorium Komputer',    'computer_lab',      40, 1, 'UNDER_RENOVATION'),
    (3, 'SR-ENG1', 'Ruang Seminar Teknik',     'seminar_room',      30, 1, 'ACTIVE');

-- ─── EQUIPMENT ───────────────────────────────────────────────
INSERT INTO equipment (equipment_code, equipment_name, equipment_type, brand, model, serial_number, status) VALUES
    -- Projectors
    ('PRJ-01', 'Proyektor Seminar Epson',        'projector',   'Epson',    'EB-L615U',   'EP2024-001', 'ACTIVE'),           -- OPERATIONAL (healthy)
    ('PRJ-02', 'Proyektor Seminar BenQ',         'projector',   'BenQ',     'LU930',      'BQ2023-002', 'UNDER_MAINTENANCE'), -- BROKEN (for test 4 & 5)
    ('PRJ-03', 'Proyektor Auditorium ViewSonic', 'projector',   'ViewSonic','PA503X',     'VS2022-003', 'ACTIVE'),           -- OPERATIONAL
    ('PRJ-04', 'Proyektor Kuliah Panasonic',     'projector',   'Panasonic','PT-MZ570',   'PN2024-004', 'ACTIVE'),           -- OPERATIONAL (contradiction test: DB says ACTIVE, FS says FAULTY)
    -- Microphones
    ('MIC-01', 'Mikrofon Wireless Shure',        'microphone',  'Shure',    'ULXD2/B58',  'SH2024-001', 'ACTIVE'),
    ('MIC-02', 'Mikrofon Kabel Audio-Technica',  'microphone',  'Audio-Technica','AT4022','AT2023-001', 'ACTIVE'),
    ('MIC-03', 'Mikrofon Clip-On Seminar',       'microphone',  'Sennheiser','EW 100 G4', 'SE2024-001', 'ACTIVE'),
    -- Sound systems
    ('SND-01', 'Sound System Auditorium JBL',    'sound_system','JBL',      'PRX812W',    'JB2021-001', 'ACTIVE'),
    ('SND-02', 'Sound System Portable Yamaha',   'sound_system','Yamaha',   'DXR10mkII',  'YM2023-001', 'ACTIVE'),
    -- Smartboards
    ('SBD-01', 'Smartboard Samsung Flip',        'smartboard',  'Samsung',  'WM85B',      'SM2024-001', 'ACTIVE');

-- ─── ROOM EQUIPMENT ASSIGNMENTS ──────────────────────────────
INSERT INTO room_equipment (room_id, equipment_id, is_primary) VALUES
    -- AUD-01 (Auditorium Utama): PRJ-03, MIC-01, SND-01
    (1, 3, 1),  -- PRJ-03 (primary projector)
    (1, 5, 1),  -- MIC-01 (wireless mic)
    (1, 8, 1),  -- SND-01 (main sound system)
    -- SR-101 (Seminar 101): PRJ-01, MIC-02
    (2, 1, 1),  -- PRJ-01 (ACTIVE — healthy)
    (2, 6, 1),  -- MIC-02
    -- SR-102 (Seminar 102): PRJ-02 (UNDER_MAINTENANCE), MIC-03
    (3, 2, 1),  -- PRJ-02 (UNDER_MAINTENANCE — for equipment fail tests)
    (3, 7, 1),  -- MIC-03
    -- CR-301 (Conference): SBD-01
    (4, 10, 1), -- SBD-01
    -- LH-201 (Kuliah 201): PRJ-04 (DB=ACTIVE but FS=FAULTY — conflict test)
    (5, 4, 1),  -- PRJ-04 (DB says ACTIVE, filesystem says FAULTY — contradiction)
    -- LH-202 (Kuliah 202): PRJ-01, SND-02
    (6, 1, 0),  -- PRJ-01 (shared, non-primary)
    (6, 9, 1),  -- SND-02
    -- SR-ENG1 (Seminar Teknik): MIC-03
    (8, 7, 0);  -- MIC-03 (shared)

-- ─── USERS ───────────────────────────────────────────────────
INSERT INTO users (employee_id, full_name, email, department, role) VALUES
    ('FAC-001', 'Dr. Sari Dewi Kusuma',     'sari.dewi@kampus.ac.id',      'Fakultas Ilmu Komputer',       'faculty'),
    ('FAC-002', 'Prof. Bambang Wiranto',    'bambang.w@kampus.ac.id',      'Fakultas Teknik',              'faculty'),
    ('STF-001', 'Andi Pratama',             'andi.pratama@kampus.ac.id',   'Biro Akademik & Kemahasiswaan','staff'),
    ('STF-002', 'Rina Suhartini',           'rina.s@kampus.ac.id',         'Biro Umum & Fasilitas',        'staff'),
    ('ADM-001', 'Sistem CampusFlow',        'system@campusflow.test',      'Sistem Informasi',             'admin'),
    ('STU-001', 'Budi Santoso',             'budi.s@student.kampus.ac.id', 'Himpunan Mahasiswa TI',        'student');

-- ─── EXISTING BOOKINGS (to create conflict scenarios) ─────────
INSERT INTO bookings (booking_reference, room_id, user_id, event_name, booking_date, start_time, end_time, attendee_count, status, confirmed_at) VALUES

    -- [AUD-01] Benchmark date 2026-09-23 morning OCCUPIED (Test 2 — Room Unavailable)
    ('BK-2026-001', 1, 1, 'Seminar Nasional Kecerdasan Buatan',
     '2026-09-23', '08:00', '12:00', 250, 'CONFIRMED',
     '2026-09-20T10:00:00Z'),

    -- [AUD-01] 2026-09-23 afternoon FREE (Test 1 success can use 13:00-15:00)

    -- [SR-101] Wednesday occupied — Capacity also insufficient for 100 pax (Test 3)
    ('BK-2026-002', 2, 2, 'Rapat Koordinasi Program Studi',
     '2026-09-23', '13:00', '15:00', 30, 'CONFIRMED',
     '2026-09-20T11:00:00Z'),

    -- [AUD-01] Full-day block on 2026-09-24 (for duplicate test baseline)
    ('BK-2026-003', 1, 3, 'Dies Natalis Kampus Ke-50',
     '2026-09-24', '07:00', '21:00', 280, 'CONFIRMED',
     '2026-09-18T09:00:00Z'),

    -- [LH-201] Free — but PRJ-04 has filesystem contradiction (Test 8)
    -- [SR-102] Free — but PRJ-02 is UNDER_MAINTENANCE in both DB and FS (Test 4)

    -- Completed historical booking (for realistic data)
    ('BK-2026-000', 1, 1, 'Orientasi Mahasiswa Baru 2026',
     '2026-09-10', '08:00', '17:00', 290, 'COMPLETED',
     '2026-09-05T08:00:00Z'),

    -- [SR-102] Booking on 2026-09-25 (PRJ-02 is UNDER_MAINTENANCE — test 4 uses SR-102)
    ('BK-2026-004', 3, 4, 'Rapat Tim Kurikulum',
     '2026-09-25', '09:00', '11:00', 15, 'CONFIRMED',
     '2026-09-19T08:00:00Z');
