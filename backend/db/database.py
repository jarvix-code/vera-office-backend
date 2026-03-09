"""
VERA Office - Datenbank Setup
SQLite + SQLAlchemy mit einfacher Migration
"""
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
