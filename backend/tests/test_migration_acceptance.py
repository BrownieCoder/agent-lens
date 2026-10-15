"""Migration failure must preserve the original schema and data, not just raise."""

import sqlite3

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.db import Base, migrate_sqlite_human_reviews
from app.models.evaluation import Evaluation
from app.models.human_review import HumanReview
from app.models.run import WorkflowRun


def test_failed_legacy_migration_rolls_back_ddl_and_remains_repeatable(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'synthetic-legacy.db'}")
    with engine.begin() as connection:
        # Unsupported legacy shape deliberately fails while copying required columns.
        connection.exec_driver_sql("CREATE TABLE human_reviews (id INTEGER PRIMARY KEY, run_id INTEGER, notes TEXT)")
        connection.exec_driver_sql("CREATE INDEX ix_legacy_notes ON human_reviews (notes)")
        connection.exec_driver_sql("INSERT INTO human_reviews VALUES (1, 7, 'synthetic preservation marker')")
    for _ in range(2):
        with pytest.raises(Exception):
            migrate_sqlite_human_reviews(engine)
        assert inspect(engine).get_table_names() == ["human_reviews"]
        assert {x["name"] for x in inspect(engine).get_indexes("human_reviews")} == {"ix_legacy_notes"}
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT * FROM human_reviews").all() == [(1, 7, "synthetic preservation marker")]
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
    engine.dispose()


def test_sqlite_backup_restore_preserves_exact_review_binding(tmp_path):
    original = tmp_path / "synthetic-original.db"
    backup = tmp_path / "synthetic-backup.db"
    restored = tmp_path / "synthetic-restored.db"
    engine = create_engine(f"sqlite:///{original}")
    Base.metadata.create_all(engine)
    scores = dict.fromkeys(("clarity_score", "evidence_score", "risk_coverage_score",
                            "specificity_score", "actionability_score", "novelty_score", "overall_score"), 3)
    with Session(engine) as db:
        run = WorkflowRun(workflow_name="restore-qa", source_type="synthetic", input_text="fixed input",
                          output_text="fixed output", prompt_version="v1", model_name="fixed-model")
        db.add(run)
        db.flush()
        first = Evaluation(run_id=run.id, evaluator_type="mock", evaluator_model="fixture-v1", **scores)
        second = Evaluation(run_id=run.id, evaluator_type="mock", evaluator_model="fixture-v2", **scores)
        db.add_all([first, second])
        db.flush()
        review = HumanReview(evaluation_id=first.id, reviewer="synthetic-reviewer", **scores)
        db.add(review)
        db.commit()
        run_id, first_id, second_id, review_id = run.id, first.id, second.id, review.id
    engine.dispose()  # Supported recovery procedure stops the app before restore.
    with sqlite3.connect(original) as source, sqlite3.connect(backup) as destination:
        source.backup(destination)
    # Later modifications must not leak into the snapshot.
    with sqlite3.connect(original) as source:
        source.execute("UPDATE workflow_runs SET output_text='later synthetic version'")
    with sqlite3.connect(backup) as source, sqlite3.connect(restored) as destination:
        source.backup(destination)
        assert destination.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert destination.execute("PRAGMA foreign_key_check").fetchall() == []
    restored_engine = create_engine(f"sqlite:///{restored}")
    Base.metadata.create_all(restored_engine)
    migrate_sqlite_human_reviews(restored_engine)
    migrate_sqlite_human_reviews(restored_engine)  # Repeated startup is idempotent.
    with Session(restored_engine) as db:
        assert db.get(WorkflowRun, run_id).output_text == "fixed output"
        assert db.get(HumanReview, review_id).evaluation_id == first_id
        assert db.get(HumanReview, review_id).evaluation.evaluator_model == "fixture-v1"
        assert db.get(Evaluation, second_id).evaluator_model == "fixture-v2"
        assert db.query(WorkflowRun).count() == 1
        assert db.query(Evaluation).count() == 2
    restored_engine.dispose()
