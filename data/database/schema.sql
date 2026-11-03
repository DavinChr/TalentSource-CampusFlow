-- =============================================================
-- CampusFlow Database Schema
-- SQLite 3 — WAL Mode, Foreign Keys Enabled
-- =============================================================

-- ─── PRAGMA CONFIGURATION ────────────────────────────────────
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous  = NORMAL;
PRAGMA busy_timeout = 5000;

-- =============================================================
-- TABLE: buildings
-- =============================================================
CREATE TABLE IF NOT EXISTS buildings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    address     TEXT,
    floors      INTEGER NOT NULL DEFAULT 1 CHECK(floors > 0),
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- =============================================================
-- TABLE: rooms
-- =============================================================
CREATE TABLE IF NOT EXISTS rooms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    building_id INTEGER NOT NULL REFERENCES buildings(id) ON DELETE CASCADE,
    room_code   TEXT    NOT NULL UNIQUE,
    room_name   TEXT    NOT NULL,
    room_type   TEXT    NOT NULL CHECK(room_type IN (
                    'auditorium', 'seminar_room', 'lecture_hall',
                    'conference_room', 'computer_lab', 'laboratory',
                    'multipurpose', 'multifungsi'
                )),
    capacity    INTEGER NOT NULL CHECK(capacity > 0),
    floor       INTEGER NOT NULL DEFAULT 1,
    status      TEXT    NOT NULL DEFAULT 'ACTIVE'
                        CHECK(status IN ('ACTIVE', 'INACTIVE', 'UNDER_RENOVATION')),
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_rooms_building  ON rooms(building_id);
CREATE INDEX IF NOT EXISTS idx_rooms_type      ON rooms(room_type);
CREATE INDEX IF NOT EXISTS idx_rooms_capacity  ON rooms(capacity);
CREATE INDEX IF NOT EXISTS idx_rooms_status    ON rooms(status);

-- =============================================================
-- TABLE: equipment
-- =============================================================
CREATE TABLE IF NOT EXISTS equipment (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_code  TEXT    NOT NULL UNIQUE,
    equipment_name  TEXT    NOT NULL,
    equipment_type  TEXT    NOT NULL CHECK(equipment_type IN (
                        'projector', 'microphone', 'sound_system',
                        'whiteboard', 'smartboard', 'computer',
                        'video_conferencing', 'air_conditioning', 'lighting', 'stage'
                    )),
    brand           TEXT,
    model           TEXT,
    serial_number   TEXT,
    status          TEXT    NOT NULL DEFAULT 'ACTIVE'
                            CHECK(status IN (
                                'ACTIVE', 'INACTIVE',
                                'UNDER_MAINTENANCE', 'DECOMMISSIONED'
                            )),
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    last_updated    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_equipment_type   ON equipment(equipment_type);
CREATE INDEX IF NOT EXISTS idx_equipment_status ON equipment(status);

-- =============================================================
-- TABLE: room_equipment
-- =============================================================
CREATE TABLE IF NOT EXISTS room_equipment (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id         INTEGER NOT NULL REFERENCES rooms(id)      ON DELETE CASCADE,
    equipment_id    INTEGER NOT NULL REFERENCES equipment(id)  ON DELETE CASCADE,
    is_primary      INTEGER NOT NULL DEFAULT 1 CHECK(is_primary IN (0, 1)),
    assigned_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE(room_id, equipment_id)
);

CREATE INDEX IF NOT EXISTS idx_room_equipment_room  ON room_equipment(room_id);
CREATE INDEX IF NOT EXISTS idx_room_equipment_equip ON room_equipment(equipment_id);

-- =============================================================
-- TABLE: users
-- =============================================================
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT    NOT NULL UNIQUE,
    full_name   TEXT    NOT NULL,
    email       TEXT    NOT NULL UNIQUE,
    department  TEXT    NOT NULL,
    role        TEXT    NOT NULL CHECK(role IN (
                    'faculty', 'staff', 'student', 'admin'
                )),
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- =============================================================
-- TABLE: bookings
-- =============================================================
CREATE TABLE IF NOT EXISTS bookings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_reference   TEXT    NOT NULL UNIQUE,
    room_id             INTEGER NOT NULL REFERENCES rooms(id),
    user_id             INTEGER NOT NULL REFERENCES users(id),
    event_name          TEXT    NOT NULL,
    booking_date        TEXT    NOT NULL,       -- YYYY-MM-DD
    start_time          TEXT    NOT NULL,       -- HH:MM
    end_time            TEXT    NOT NULL,       -- HH:MM
    attendee_count      INTEGER NOT NULL CHECK(attendee_count > 0),
    status              TEXT    NOT NULL DEFAULT 'CONFIRMED'
                                CHECK(status IN ('CONFIRMED', 'CANCELLED', 'COMPLETED')),
    notes               TEXT,
    created_at          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    confirmed_at        TEXT,
    CHECK (start_time < end_time)
);

-- Index for conflict detection — covers the WHERE status = 'CONFIRMED' partial scope
CREATE INDEX IF NOT EXISTS idx_bookings_room_date
    ON bookings(room_id, booking_date, start_time, end_time);

CREATE INDEX IF NOT EXISTS idx_bookings_date
    ON bookings(booking_date);

CREATE INDEX IF NOT EXISTS idx_bookings_status
    ON bookings(status);

-- =============================================================
-- TABLE: audit_logs
-- =============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id        TEXT    NOT NULL,
    booking_id      INTEGER REFERENCES bookings(id),   -- NULL when booking failed
    step_index      INTEGER NOT NULL,
    step_name       TEXT    NOT NULL,
    workflow_status TEXT    NOT NULL,
    evidence_json   TEXT,                              -- JSON string of MCP tool result
    decision        TEXT,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_trace   ON audit_logs(trace_id);
CREATE INDEX IF NOT EXISTS idx_audit_booking ON audit_logs(booking_id);
