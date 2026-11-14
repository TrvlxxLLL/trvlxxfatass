"""DDL и миграции SQLite для СухоVL.

SCHEMA создаёт таблицы на чистой базе, MIGRATIONS добавляет недостающие
колонки в уже существующие базы, INDEXES выполняется после миграций.
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    photo_path TEXT,
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    confirmations INTEGER NOT NULL DEFAULT 0,
    denials INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'gone')),
    created_at TEXT NOT NULL,
    last_confirmed_at TEXT,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS uploads (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    mime TEXT NOT NULL,
    size INTEGER NOT NULL,
    ai_status TEXT NOT NULL DEFAULT 'pending',
    ai_reason TEXT,
    created_at TEXT NOT NULL,
    checked_at TEXT
);

CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    point_id INTEGER NOT NULL,
    voter TEXT NOT NULL,
    value INTEGER NOT NULL CHECK (value IN (1, -1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (point_id, voter)
);
"""

# (таблица, колонка, тип и значение по умолчанию)
MIGRATIONS = [
    ("points", "upload_id", "TEXT"),
    ("points", "address", "TEXT"),
    ("points", "photo_status", "TEXT NOT NULL DEFAULT 'none'"),
    ("points", "comment_status", "TEXT NOT NULL DEFAULT 'none'"),
    ("points", "moderation_status", "TEXT NOT NULL DEFAULT 'published'"),
    ("points", "ai_photo_verdict", "TEXT"),
    ("points", "ai_photo_reason", "TEXT"),
    ("points", "ai_comment_verdict", "TEXT"),
    ("points", "ai_comment_reason", "TEXT"),
    ("points", "moderated_by", "TEXT"),
    ("points", "moderated_at", "TEXT"),
    ("points", "denials", "INTEGER NOT NULL DEFAULT 0"),
    ("points", "last_confirmed_at", "TEXT"),
    ("points", "expires_at", "TEXT"),
]

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_points_moderation
    ON points (moderation_status);
CREATE INDEX IF NOT EXISTS idx_points_photo_path
    ON points (photo_path);
CREATE INDEX IF NOT EXISTS idx_points_expires
    ON points (expires_at);
CREATE INDEX IF NOT EXISTS idx_uploads_created
    ON uploads (created_at);
CREATE INDEX IF NOT EXISTS idx_votes_point
    ON votes (point_id);
"""
