"""
Database layer for SEOAuditMachine (SQLite)

- Versioned migrations (schema_migrations)
- Core entities: sites, sitemaps, urls, inspections
- Convenience helpers for common CRUD

This module is intentionally framework‑free and synchronous.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---- Connection helpers ----------------------------------------------------

DEFAULT_DB_PATH = Path(".seoaudmach") / "seo_audit_machine.db"

def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with sane defaults and FK enforcement."""
    p = Path(db_path)
    _ensure_dir(p)
    first_time = not p.exists()
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    if first_time:
        migrate(conn)
    return conn

# ---- Migrations ------------------------------------------------------------

MIGRATIONS: List[Tuple[int, str]] = [
    # 1: initial schema
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     INTEGER PRIMARY KEY,
            applied_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sites (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT,
            base_url    TEXT    NOT NULL UNIQUE,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sitemaps (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id        INTEGER NOT NULL,
            url            TEXT    NOT NULL,
            last_submitted TEXT,
            is_pending     INTEGER,
            discovered_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE CASCADE
        );

        CREATE UNIQUE INDEX IF NOT EXISTS sitemaps_site_url_uq
            ON sitemaps(site_id, url);

        CREATE TABLE IF NOT EXISTS urls (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id      INTEGER NOT NULL,
            url          TEXT    NOT NULL,
            first_seen   TEXT    NOT NULL DEFAULT (datetime('now')),
            last_seen    TEXT,
            in_sitemap   INTEGER NOT NULL DEFAULT 0,
            http_status  INTEGER,
            last_crawled TEXT,
            last_modified TEXT,
            change_freq TEXT,
            priority REAL,
            FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE CASCADE
        );

        CREATE UNIQUE INDEX IF NOT EXISTS urls_site_url_uq
            ON urls(site_id, url);

        CREATE INDEX IF NOT EXISTS urls_site_idx ON urls(site_id);

        CREATE INDEX IF NOT EXISTS idx_urls_siteid_url ON urls(site_id, url);

        CREATE TABLE IF NOT EXISTS inspections (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            url_id             INTEGER NOT NULL,
            inspected_at       TEXT    NOT NULL DEFAULT (datetime('now')),
            index_status       TEXT,
            coverage_state     TEXT,
            robots_txt_state   TEXT,
            canonical_url      TEXT,
            page_fetch_state   TEXT,
            last_crawl_time    TEXT,
            referring_urls_json TEXT,
            raw_json           TEXT,
            FOREIGN KEY(url_id) REFERENCES urls(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS inspections_url_idx ON inspections(url_id);
        """,
    ),
]

def _applied_versions(conn: sqlite3.Connection) -> List[int]:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     INTEGER PRIMARY KEY,
            applied_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    return [r[0] for r in rows]

def migrate(conn: sqlite3.Connection) -> None:
    """Apply pending migrations in order."""
    applied = set(_applied_versions(conn))
    for version, sql in MIGRATIONS:
        if version in applied:
            continue
        with conn:
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))

def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> Path:
    """Initialize database file and apply migrations. Returns the DB path."""
    with connect(db_path) as conn:
        migrate(conn)
    return Path(db_path)

# ---- Data classes (lightweight, optional use) ------------------------------

@dataclass
class Sitemap:
    id: int
    site_id: int
    url: str
    last_submitted: Optional[str] = None
    is_pending: Optional[str] = None
    discovered_at: Optional[int] = None

@dataclass
class Site:
    id: int
    base_url: str
    name: Optional[str] = None

@dataclass
class URLRow:
    id: int
    site_id: int
    url: str
    in_sitemap: bool
    http_status: Optional[int] = None

# ---- CRUD helpers ----------------------------------------------------------

def add_site(conn: sqlite3.Connection, base_url: str, name: Optional[str] = None) -> int:
    """Insert a site if missing; return id."""
    with conn:
        cur = conn.execute("SELECT id FROM sites WHERE base_url = ?", (base_url,))
        row = cur.fetchone()
        if row:
            if name:
                conn.execute("UPDATE sites SET name = COALESCE(?, name) WHERE id = ?", (name, row[0]))
            return int(row[0])
        cur = conn.execute("INSERT INTO sites(base_url, name) VALUES (?, ?)", (base_url, name))
        return int(cur.lastrowid)

def get_site_by_url(conn: sqlite3.Connection, base_url: str) -> Optional[Site]:
    row = conn.execute("SELECT id, base_url, name FROM sites WHERE base_url = ?", (base_url,)).fetchone()
    return Site(**dict(row)) if row else None

def get_site(conn: sqlite3.Connection, site_id: int) -> Optional[Site]:
    row = conn.execute("SELECT id, base_url, name FROM sites WHERE id = ?", (site_id,)).fetchone()
    return Site(**dict(row)) if row else None

def get_sites(conn: sqlite3.Connection) -> List[Site]:
    rows = conn.execute("SELECT id, base_url, name FROM sites ORDER BY id").fetchall()
    return [Site(**dict(r)) for r in rows]

def get_sitemaps_by_url(conn: sqlite3.Connection, site_url) -> List[Site]:
    site = get_site_by_url(conn, site_url)
    site_id = site.id if site else None
    if not site_id:
        return []
    rows = conn.execute("SELECT id, site_id, url, last_submitted, is_pending, discovered_at FROM sitemaps WHERE site_id = ? ORDER BY id", (site_id,)).fetchall()
    return [Sitemap(**dict(r)) for r in rows]

def get_all_sitemaps(conn: sqlite3.Connection) -> List[Site]:
    rows = conn.execute("SELECT id, site_id, url, last_submitted, is_pending FROM sitemaps ORDER BY id").fetchall()
    return [Sitemap(**dict(r)) for r in rows]

def upsert_sitemap(
    conn: sqlite3.Connection,
    site_id: int,
    url: str,
    last_submitted: Optional[str] = None,
    is_pending: Optional[bool] = None,
) -> int:
    with conn:
        cur = conn.execute(
            "SELECT id FROM sitemaps WHERE site_id = ? AND url = ?",
            (site_id, url),
        )
        row = cur.fetchone()
        if row:
            conn.execute(
                "UPDATE sitemaps SET last_submitted = ?, is_pending = ? WHERE id = ?",
                (last_submitted, int(is_pending) if is_pending is not None else None, row[0]),
            )
            return int(row[0])
        cur = conn.execute(
            "INSERT INTO sitemaps(site_id, url, last_submitted, is_pending) VALUES (?,?,?,?)",
            (site_id, url, last_submitted, int(is_pending) if is_pending is not None else None),
        )
        return int(cur.lastrowid)

def upsert_url(
    conn: sqlite3.Connection,
    site_id: int,
    url: str,
    in_sitemap: Optional[bool] = None,
    http_status: Optional[int] = None,
    seen_now: bool = True,
    last_modified: Optional[str] = None,
    change_freq: Optional[str] = None,
    priority: Optional[float] = None,
) -> int:
    """Insert URL if missing or update attributes; return url_id."""
    with conn:
        row = conn.execute(
            "SELECT id FROM urls WHERE site_id = ? AND url = ?",
            (site_id, url),
        ).fetchone()
        if row:
            sql = ["UPDATE urls SET "]
            params: List[Any] = []
            sets: List[str] = []
            if in_sitemap is not None:
                sets.append("in_sitemap = ?")
                params.append(1 if in_sitemap else 0)
            if http_status is not None:
                sets.append("http_status = ?")
                params.append(http_status)
            if last_modified is not None:
                sets.append("last_modified = ?")
                params.append(last_modified)
            if change_freq is not None:
                sets.append("change_freq = ?")
                params.append(change_freq)
            if priority is not None:
                sets.append("priority = ?")
                params.append(priority)
            if seen_now:
                sets.append("last_seen = datetime('now')")
            if sets:
                sql.append(", ".join(sets))
                sql.append(" WHERE id = ?")
                params.append(int(row[0]))
                conn.execute("".join(sql), params)
            return int(row[0])
        cur = conn.execute(
            "INSERT INTO urls(site_id, url, in_sitemap, http_status, last_seen) VALUES (?,?,?,?, CASE WHEN ? THEN datetime('now') END)",
            (site_id, url, 1 if in_sitemap else 0, http_status, 1 if seen_now else 0),
        )
        return int(cur.lastrowid)

def list_urls(conn: sqlite3.Connection, site_id: int) -> List[URLRow]:
    rows = conn.execute(
        "SELECT id, site_id, url, in_sitemap, http_status FROM urls WHERE site_id = ? ORDER BY id",
        (site_id,),
    ).fetchall()
    return [URLRow(**dict(r)) for r in rows]

def record_inspection(
    conn: sqlite3.Connection,
    url_id: int,
    *,
    index_status: Optional[str] = None,
    coverage_state: Optional[str] = None,
    robots_txt_state: Optional[str] = None,
    canonical_url: Optional[str] = None,
    page_fetch_state: Optional[str] = None,
    last_crawl_time: Optional[str] = None,
    referring_urls: Optional[Iterable[str]] = None,
    raw: Optional[Dict[str, Any]] = None,
) -> int:
    """Record a single URL Inspection result.

    `raw` should be the full GSC response body (or trimmed).
    """
    with conn:
        cur = conn.execute(
            """
            INSERT INTO inspections (
                url_id, index_status, coverage_state, robots_txt_state, canonical_url,
                page_fetch_state, last_crawl_time, referring_urls_json, raw_json
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                url_id,
                index_status,
                coverage_state,
                robots_txt_state,
                canonical_url,
                page_fetch_state,
                last_crawl_time,
                json.dumps(list(referring_urls) if referring_urls else []),
                json.dumps(raw or {}),
            ),
        )
        return int(cur.lastrowid)

def latest_inspection(conn: sqlite3.Connection, url_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM inspections WHERE url_id = ? ORDER BY inspected_at DESC, id DESC LIMIT 1",
        (url_id,),
    ).fetchone()
    return dict(row) if row else None

# ---- Convenience reporting --------------------------------------------------

def not_indexed_but_internally_linked(conn: sqlite3.Connection, site_id: int) -> List[Dict[str, Any]]:
    """Example report: URLs we know about that are not indexed (based on latest inspection)."""
    sql = """
    WITH latest AS (
        SELECT i.*
        FROM inspections i
        JOIN (
            SELECT url_id, MAX(inspected_at) AS max_t
            FROM inspections
            GROUP BY url_id
        ) t ON t.url_id = i.url_id AND t.max_t = i.inspected_at
    )
    SELECT u.id AS url_id, u.url, l.index_status, l.coverage_state
    FROM urls u
    LEFT JOIN latest l ON l.url_id = u.id
    WHERE u.site_id = ? AND (l.index_status IS NULL OR l.index_status != 'INDEXED')
    ORDER BY u.id;
    """
    rows = conn.execute(sql, (site_id,)).fetchall()
    return [dict(r) for r in rows]
