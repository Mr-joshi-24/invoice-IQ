from sqlalchemy import inspect, text
from backend.app.database.session import engine
from backend.app.database.base import Base
import backend.app.models  # Registers all models with Base.metadata
from backend.app.core.logging import logger


def init_db() -> None:
    """
    Creates all database tables defined in the metadata.
    Applies non-destructive schema migrations for newly introduced columns.
    Safe to run repeatedly; preserves existing user and invoice data.
    """
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    # Safe lightweight schema evolution for existing SQLite/Postgres tables
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if "extracted_fields" in tables:
            cols = [col["name"] for col in inspector.get_columns("extracted_fields")]
            if "original_value" not in cols:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE extracted_fields ADD COLUMN original_value TEXT"))
                    conn.commit()
                    logger.info("Migrated schema: added 'original_value' column to extracted_fields table.")

        if "documents" in tables:
            cols = [col["name"] for col in inspector.get_columns("documents")]
            if "user_id" not in cols:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN user_id VARCHAR(36)"))
                    conn.commit()
                    logger.info("Migrated schema: added 'user_id' column to documents table.")
    except Exception as e:
        logger.warning(f"Schema migration check notice: {e}")

    logger.info("Database tables initialized successfully.")


def reset_db() -> None:
    """
    Drops and recreates all database tables.
    Use ONLY in development or automated testing.
    """
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.info("Database reset complete.")


if __name__ == "__main__":
    init_db()
