from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import settings

sync_database_url = settings.database_url.replace(
    "postgresql+asyncpg://",
    "postgresql+psycopg://",
)

sync_engine = create_engine(
    sync_database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
)
