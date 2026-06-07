from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.core.config import settings


def ensure_pgvector_extension(engine: Engine):
    if not settings.SQLALCHEMY_DATABASE_URI.startswith("postgres"):
        return

    import logging
    logger = logging.getLogger(__name__)

    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    except Exception as e:
        logger.warning(f"Could not ensure pgvector extension (database might be unavailable): {e}")
