from collections.abc import Generator
from datetime import datetime, timezone
import sqlite3

from sqlalchemy import DateTime, create_engine, event, inspect
from sqlalchemy.types import TypeDecorator
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class UTCDateTime(TypeDecorator):
    """Persist UTC and return aware timestamps, including SQLite's naive values.

    Existing application timestamps were generated in UTC; the legacy naive
    representation therefore denotes UTC. No database schema rewrite is needed.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


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


def _rebuild_table(connection, table, defaults: dict[str, str]) -> None:
    quote = connection.dialect.identifier_preparer.quote
    name = table.name
    columns = {column["name"] for column in inspect(connection).get_columns(name)}
    legacy = name + "_legacy"
    if inspect(connection).has_table(legacy):
        raise RuntimeError(f"Unexpected migration backup table {legacy}; restore a verified backup")
    connection.exec_driver_sql(f"ALTER TABLE {quote(name)} RENAME TO {quote(legacy)}")
    for index in inspect(connection).get_indexes(legacy):
        connection.exec_driver_sql(f"DROP INDEX IF EXISTS {quote(index['name'])}")
    table.create(bind=connection)
    names = [column.name for column in table.columns]
    values = [quote(name) if name in columns else defaults[name] for name in names]
    if name == "workflow_runs" and "usage_source" not in columns:
        # Legacy zero defaults cannot distinguish unknown from measured zero.
        # Preserve exact historical fields separately and conservatively treat zero
        # as unknown in current aggregates rather than inventing measurement evidence.
        for field in ("token_input", "token_output", "estimated_cost", "latency_ms"):
            values[names.index(field)] = f"NULLIF({quote(field)}, 0)"
    connection.exec_driver_sql(
        f"INSERT INTO {quote(name)} ({', '.join(map(quote, names))}) "
        f"SELECT {', '.join(values)} FROM {quote(legacy)}"
    )
    connection.exec_driver_sql(f"DROP TABLE {quote(legacy)}")


def migrate_sqlite_human_reviews(target_engine: Engine = engine) -> None:
    """Atomically upgrade supported alpha schemas; any failure leaves all originals intact.

    sqlite3 legacy transaction mode does not BEGIN for DDL. Explicit SQL BEGIN is
    essential: SQLAlchemy's logical begin alone cannot roll back ALTER/CREATE.
    """
    if target_engine.dialect.name != "sqlite":
        return
    from .models import HumanReview, WorkflowRun, Evaluation

    with target_engine.connect() as connection:
        connection.commit()
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.exec_driver_sql("PRAGMA legacy_alter_table=ON")
        connection.commit()
        try:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            inspector = inspect(connection)
            if inspector.has_table("workflow_runs"):
                columns = {c["name"]: c for c in inspector.get_columns("workflow_runs")}
                fks = inspector.get_foreign_keys("workflow_runs")
                if "usage_source" not in columns or "generation_parameters" not in columns or "last_evaluation_error" not in columns or not columns["estimated_cost"]["nullable"] or not any(fk["referred_table"] == "regression_cases" for fk in fks):
                    _rebuild_table(connection, WorkflowRun.__table__, { "usage_source": "'legacy-unverified'", "legacy_usage": "json_object('token_input', token_input, 'token_output', token_output, 'estimated_cost', estimated_cost, 'latency_ms', latency_ms)", "last_evaluation_error": "NULL", "prompt_template_hash": "NULL", "generation_parameters": "NULL", "dataset_name": "NULL", "experiment_name": "NULL"})
            if inspector.has_table("evaluations"):
                columns = {c["name"] for c in inspect(connection).get_columns("evaluations")}
                if "rubric_version" not in columns or "request_id" not in columns:
                    _rebuild_table(connection, Evaluation.__table__, {"rubric_version": "'research-report-v1'", "request_id": "NULL"})
            if inspector.has_table("human_reviews"):
                columns = {c["name"] for c in inspect(connection).get_columns("human_reviews")}
                if "run_id" in columns or "scores_edited_after_reveal" not in columns or "original_scores" not in columns:
                    _rebuild_table(connection, HumanReview.__table__, {"scores_edited_after_reveal": "0", "original_scores": "NULL"})
            violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError("Database migration found invalid foreign keys; restore or repair the source backup")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.exec_driver_sql("PRAGMA legacy_alter_table=OFF")
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()


def init_db() -> None:
    from . import models  # noqa: F401

    migrate_sqlite_human_reviews()
    Base.metadata.create_all(bind=engine)
