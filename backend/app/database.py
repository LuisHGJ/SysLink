"""Conexão com o banco de dados."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base para todos os models SQLAlchemy."""


def get_db():
    """Dependency: fornece uma sessão por request e fecha ao final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
