from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from config.settings import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> tuple[bool, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "PostgreSQL connection successful"
    except Exception as exc:  # pragma: no cover
        return False, str(exc)
