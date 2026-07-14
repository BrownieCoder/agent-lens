from collections.abc import Generator
import sqlite3

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_sqlite_human_reviews(target_engine: Engine = engine) -> None:
    """Rebuild the unreleased legacy review table without losing local review data."""
    if target_engine.dialect.name != "sqlite":
        return
    from .models.human_review import HumanReview

    with target_engine.connect() as connection:
        inspector = inspect(connection)
        if not inspector.has_table("human_reviews"):
            return
        legacy_columns = {column["name"] for column in inspector.get_columns("human_reviews")}
        if "run_id" not in legacy_columns and "scores_edited_after_reveal" in legacy_columns:
            return

        quote = connection.dialect.identifier_preparer.quote
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
        transaction = connection.begin()
        try:
            connection.exec_driver_sql(
                "ALTER TABLE human_reviews RENAME TO human_reviews_legacy"
            )
            for index in inspect(connection).get_indexes("human_reviews_legacy"):
                connection.exec_driver_sql(f"DROP INDEX IF EXISTS {quote(index['name'])}")
            HumanReview.__table__.create(bind=connection)
            target_columns = [column.name for column in HumanReview.__table__.columns]
            select_values = [
                "0" if name == "scores_edited_after_reveal" else quote(name)
                for name in target_columns
            ]
            connection.exec_driver_sql(
                f"INSERT INTO human_reviews ({', '.join(map(quote, target_columns))}) "
                f"SELECT {', '.join(select_values)} FROM human_reviews_legacy"
            )
            connection.exec_driver_sql("DROP TABLE human_reviews_legacy")
            transaction.commit()
        except Exception:
            transaction.rollback()
            raise
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    migrate_sqlite_human_reviews()
