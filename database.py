"""Database session setup (SQLAlchemy, SQLite by default)."""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Some providers (Render, Heroku) hand out "postgres://" URLs, but SQLAlchemy
# requires the "postgresql://" scheme. Normalize so either form works.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# check_same_thread only matters for SQLite + multiple threads (FastAPI workers).
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables and optionally seed Config from environment variables."""
    import models  # noqa: F401  (register models on Base before create_all)

    Base.metadata.create_all(bind=engine)
    _seed_config_from_env()


def _seed_config_from_env():
    """If the Config table is empty, seed it from .env so the app works on first boot."""
    from models import Config

    db = SessionLocal()
    try:
        if db.query(Config).first():
            return
        cfg = Config(
            instagram_access_token=os.getenv("INSTAGRAM_ACCESS_TOKEN", ""),
            instagram_business_account_id=os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", ""),
            facebook_page_id=os.getenv("FACEBOOK_PAGE_ID", ""),
            facebook_page_access_token=os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", ""),
        )
        db.add(cfg)
        db.commit()
    finally:
        db.close()
