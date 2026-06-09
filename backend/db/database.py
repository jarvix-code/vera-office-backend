"""
VERA Office - Datenbank Setup
SQLite + SQLAlchemy mit einfacher Migration
"""
import re
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from backend.config import config
from loguru import logger

Base = declarative_base()

engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False  # SQL-Queries nicht loggen (zu viel Spam)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



_GERMAN_DATE_RE = re.compile(r'^(\d{1,2})\.(\d{1,2})\.(\d{4})(?:\s+(\d{2}):(\d{2})(?::(\d{2}))?)?$')


def _normalize_de_date(val):
    """Konvertiert DD.MM.YYYY zu YYYY-MM-DD HH:MM:SS fuer SQLite."""
    if not isinstance(val, str):
        return val
    m = _GERMAN_DATE_RE.match(val.strip())
    if m:
        d, mo, y, h, mi, s = m.groups()
        h = h or '00'
        mi = mi or '00'
        s = s or '00'
        return f'{int(y):04d}-{int(mo):02d}-{int(d):02d} {h}:{mi}:{s}'
    return val


def _migrate_german_dates():
    """
    Bug #257: Konvertiert deutsche Datumsstrings (DD.MM.YYYY) in DateTime-Spalten
    der documents-Tabelle zu ISO 8601 (YYYY-MM-DD HH:MM:SS).
    Idempotent - keine Aenderungen wenn bereits korrekt.
    """
    date_cols = ['document_date', 'classified_at', 'escalated_at', 'reviewed_at', 'deleted_at']
    inspector = inspect(engine)
    existing_cols = {c['name'] for c in inspector.get_columns('documents')}
    cols_to_check = [c for c in date_cols if c in existing_cols]

    total_fixed = 0
    with engine.connect() as conn:
        for col in cols_to_check:
            rows = conn.execute(
                text(f"SELECT id, {col} FROM documents WHERE {col} LIKE '__.__.__%'")
            ).fetchall()
            for doc_id, val in rows:
                new_val = _normalize_de_date(val)
                if new_val != val:
                    conn.execute(
                        text(f"UPDATE documents SET {col}=:v WHERE id=:i"),
                        {"v": new_val, "i": doc_id}
                    )
                    total_fixed += 1
        if total_fixed:
            conn.commit()
            logger.info(f"Bug #257 Migration: {total_fixed} Datumswerte von DD.MM.YYYY nach ISO 8601 konvertiert")


def _run_migrations():
    """
    Einfache Schema-Migrationen für bestehende Datenbanken.
    Prüft ob Spalten existieren und fügt fehlende hinzu.
    """
    inspector = inspect(engine)
    
    if "users" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("users")]
        
        # Migration: role-Spalte hinzufügen (Phase 1 Rollen-System)
        if "role" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'admin' NOT NULL"))
                # Bestehende Admins als admin markieren
                conn.execute(text("UPDATE users SET role = 'admin' WHERE is_admin = 1"))
                conn.execute(text("UPDATE users SET role = 'viewer' WHERE is_admin = 0"))
                conn.commit()
            logger.info("Migration: 'role' Spalte zu users hinzugefügt")

        # Migration: Neues Auth-System (PIN + Master-PW)
        needs_commit = False
        with engine.connect() as conn:
            if "name" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN name VARCHAR(100)"))
                needs_commit = True
                logger.info("Migration: 'name' Spalte zu users hinzugefügt")
            if "master_pw_hash" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN master_pw_hash VARCHAR(255)"))
                needs_commit = True
                logger.info("Migration: 'master_pw_hash' Spalte zu users hinzugefügt")
            if "pin_hash" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN pin_hash VARCHAR(255)"))
                needs_commit = True
                logger.info("Migration: 'pin_hash' Spalte zu users hinzugefügt")
            if "modules_unlocked" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN modules_unlocked TEXT DEFAULT '[]'"))
                needs_commit = True
                logger.info("Migration: 'modules_unlocked' Spalte zu users hinzugefügt")
            if needs_commit:
                conn.commit()


    # Bug #1258: documents-Tabelle - fehlende Spalten nachträglich hinzufügen
    # Hintergrund: SQLAlchemy create_all() ändert keine bestehenden Tabellen.
    # Neue Spalten im Document-Model (document.py) müssen hier explizit migriert werden.
    if "documents" in inspector.get_table_names():
        doc_columns = {col["name"] for col in inspector.get_columns("documents")}
        doc_migrations = [
            # (column_name, DDL_definition)
            ("classification_reasoning",  "TEXT"),
            ("classification_status",     "VARCHAR(50) DEFAULT 'pending'"),
            ("user_explanation",          "TEXT"),
            ("classified_at",             "DATETIME"),
            ("confidence",                "FLOAT"),
            ("user_comment",              "TEXT"),
            ("escalated_at",              "DATETIME"),
            ("escalated_by",              "VARCHAR(128)"),
            ("reviewed_at",               "DATETIME"),
            ("dev_notes",                 "TEXT"),
            ("original_image_path",       "VARCHAR(1024)"),
            ("quality_score",             "FLOAT"),
            ("quality_issues",            "TEXT"),
            ("invoice_validation",        "VARCHAR(50)"),
            ("deleted",                   "BOOLEAN DEFAULT 0"),
            ("deleted_at",                "DATETIME"),
        ]
        doc_needs_commit = False
        with engine.connect() as conn:
            for col_name, col_def in doc_migrations:
                if col_name not in doc_columns:
                    conn.execute(text(f"ALTER TABLE documents ADD COLUMN {col_name} {col_def}"))
                    doc_needs_commit = True
                    logger.info(f"Migration Bug#1258: 'documents.{col_name}' Spalte hinzugefügt")
            if doc_needs_commit:
                conn.commit()
                logger.info("Migration Bug#1258: documents-Schema aktualisiert")

    # Bug #257: Datumsformat-Migration DD.MM.YYYY -> ISO 8601
    if "documents" in inspector.get_table_names():
        _migrate_german_dates()


def init_db():
    """Initialisiert Datenbank (erstellt Tabellen + Migrationen)."""
    from backend.models.document import Document
    from backend.models.category import Category
    from backend.models.settings import Settings as SettingsModel
    from backend.models.settings import OnboardingState
    from backend.models.user import User
    
    logger.info("Initialisiere Datenbank...")
    Base.metadata.create_all(bind=engine)
    
    # Migrationen für bestehende DBs
    _run_migrations()
    
    logger.success("Datenbank bereit")
