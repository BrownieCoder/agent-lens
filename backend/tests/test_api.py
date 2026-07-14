from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)


def override_db() -> Generator[Session, None, None]:
    with TestingSession() as session:
        yield session


app.dependency_overrides[get_db] = override_db


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


def sample_run(prompt_version: str = "v1") -> dict:
    return {
        "workflow_name": "x-signal-agent",
        "source_type": "discord",
        "input_text": "Revenue grew 12% according to the quarterly filing.",
        "output_text": (
            "Evidence: filing data shows 12% growth and improved demand.\n"
            "Risks: uncertain conversion and margin downside remain.\n"
            "Next: monitor guidance and the next filing before taking action."
        ),
        "prompt_version": prompt_version,
        "model_name": "gpt-4.1-mini",
        "token_input": 300,
        "token_output": 120,
        "estimated_cost": 0.001,
        "latency_ms": 850,
        "status": "success",
    }


def test_vertical_slice(client: TestClient):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "version": "0.1.0-alpha"}

    created = client.post("/runs", json=sample_run())
    assert created.status_code == 201
    run_id = created.json()["id"]

    evaluated = client.post(f"/runs/{run_id}/evaluate", json={"evaluator_type": "mock"})
    assert evaluated.status_code == 201
    assert 1 <= evaluated.json()["overall_score"] <= 5

    detail = client.get(f"/runs/{run_id}")
    assert detail.status_code == 200
    assert len(detail.json()["evaluations"]) == 1

    summary = client.get("/dashboard/summary")
    assert summary.status_code == 200
    assert summary.json()["total_runs"] == 1

    comparison = client.get("/dashboard/prompt-comparison")
    assert comparison.status_code == 200
    assert comparison.json()[0]["prompt_version"] == "v1"

    trends = client.get("/dashboard/trends")
    ranked = client.get("/dashboard/ranked-runs")
    assert trends.status_code == 200 and len(trends.json()) == 1
    assert ranked.status_code == 200 and ranked.json()["best"][0]["id"] == run_id

    report = client.post("/reports/evaluation-summary", json={})
    assert report.status_code == 200
    assert "Agent Lens Evaluation Summary" in report.text


def test_openai_schema_is_strict():
    from app.schemas.evaluation import EvaluationPayload

    schema = EvaluationPayload.model_json_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])


def test_deepseek_requires_api_key():
    from app.config import Settings
    from app.services.evaluator import get_evaluator

    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        get_evaluator("deepseek", Settings(deepseek_api_key=None))


def test_unknown_evaluator_is_rejected(client: TestClient):
    run_id = client.post("/runs", json=sample_run()).json()["id"]
    response = client.post(f"/runs/{run_id}/evaluate", json={"evaluator_type": "unknown"})
    assert response.status_code == 400
    assert "Unsupported evaluator backend" in response.json()["detail"]


def test_provider_failure_returns_bad_gateway(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    from app.routers import evaluations
    from app.services.evaluator import ProviderEvaluationError

    class BrokenEvaluator:
        def evaluate(self, _run):
            raise ProviderEvaluationError("Provider did not return a valid evaluation")

    monkeypatch.setattr(evaluations, "get_evaluator", lambda *_: BrokenEvaluator())
    run_id = client.post("/runs", json=sample_run()).json()["id"]
    response = client.post(f"/runs/{run_id}/evaluate", json={"evaluator_type": "openai"})
    assert response.status_code == 502
    assert response.json()["detail"] == "Provider did not return a valid evaluation"


def test_deepseek_json_output_is_validated(monkeypatch: pytest.MonkeyPatch):
    import json
    from types import SimpleNamespace

    import openai

    from app.config import Settings
    from app.models.run import WorkflowRun
    from app.services.evaluator import DeepSeekEvaluator

    payload = {
        "clarity_score": 4,
        "evidence_score": 3,
        "risk_coverage_score": 4,
        "specificity_score": 4,
        "actionability_score": 3,
        "novelty_score": 3,
        "overall_score": 3.5,
        "possible_hallucination": False,
        "too_generic": False,
        "missing_risks": False,
        "overconfident_language": False,
        "weak_evidence": False,
        "needs_human_review": False,
        "comments": "Specific and appropriately cautious.",
    }

    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["response_format"] == {"type": "json_object"}
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
            )

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["base_url"] == "https://api.deepseek.com"
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    evaluator = DeepSeekEvaluator(Settings(deepseek_api_key="test-key"))
    result = evaluator.evaluate(WorkflowRun(
        workflow_name="test", source_type="manual", input_text="input", output_text="output",
        prompt_version="v1", model_name="test",
    ))
    assert result.evaluator_model == "deepseek-v4-flash"
    assert result.payload.overall_score == 3.5


def test_filters_and_regression_case(client: TestClient):
    case = client.post("/regression-cases", json={
        "name": "Unsupported partnership claim",
        "input_text": "A social post claims a partnership.",
        "expected_focus": "Flag missing primary evidence.",
        "notes": "High hallucination risk",
    })
    assert case.status_code == 201
    case_id = case.json()["id"]

    payload = sample_run("v2") | {"regression_case_id": case_id}
    assert client.post("/runs", json=payload).status_code == 201
    assert len(client.get("/runs?prompt_version=v2").json()) == 1
    assert len(client.get(f"/regression-cases/{case_id}/runs").json()) == 1


def review_payload(evaluation_id: int, reviewer: str = "local-reviewer", score: float = 3.0) -> dict:
    return {
        "evaluation_id": evaluation_id,
        "reviewer": reviewer,
        "review_decision": "pending",
        "rubric_version": "research-report-v1",
        "clarity_score": score,
        "evidence_score": score,
        "risk_coverage_score": score,
        "specificity_score": score,
        "actionability_score": score,
        "novelty_score": score,
        "overall_score": score,
        "notes": "Synthetic calibration fixture.",
    }


def add_evaluation(run_id: int, score: float, model: str = "judge-v1") -> int:
    from app.models.evaluation import Evaluation

    with TestingSession() as db:
        evaluation = Evaluation(
            run_id=run_id,
            evaluator_type="llm",
            evaluator_model=model,
            clarity_score=score,
            evidence_score=score,
            risk_coverage_score=score,
            specificity_score=score,
            actionability_score=score,
            novelty_score=score,
            overall_score=score,
            comments="Fixture evaluation.",
        )
        db.add(evaluation)
        db.commit()
        return evaluation.id


def test_human_review_lifecycle_and_exact_evaluation_binding(client: TestClient):
    first_run = client.post("/runs", json=sample_run()).json()
    second_run = client.post("/runs", json=sample_run("v2")).json()
    evaluation_id = add_evaluation(first_run["id"], 4.0)

    created = client.post(
        f"/runs/{first_run['id']}/human-reviews",
        json=review_payload(evaluation_id),
    )
    assert created.status_code == 201
    assert created.json()["evaluation_id"] == evaluation_id
    review_id = created.json()["id"]

    duplicate = client.post(
        f"/runs/{first_run['id']}/human-reviews",
        json=review_payload(evaluation_id),
    )
    assert duplicate.status_code == 409

    mismatched = client.post(
        f"/runs/{second_run['id']}/human-reviews",
        json=review_payload(evaluation_id, reviewer="other-reviewer"),
    )
    assert mismatched.status_code == 422

    updated_payload = review_payload(evaluation_id, score=3.5) | {
        "review_decision": "adjust",
        "notes": "Evidence was weaker than the model score suggested.",
    }
    updated_payload.pop("evaluation_id")
    updated = client.put(f"/human-reviews/{review_id}", json=updated_payload)
    assert updated.status_code == 200
    assert updated.json()["overall_score"] == 3.5
    assert updated.json()["review_decision"] == "pending"
    assert updated.json()["scores_edited_after_reveal"] is True
    decided = client.put(f"/human-reviews/{review_id}", json=updated_payload)
    assert decided.status_code == 200
    assert decided.json()["review_decision"] == "adjust"

    second = client.post(
        f"/runs/{first_run['id']}/human-reviews",
        json=review_payload(evaluation_id, reviewer="other-reviewer"),
    )
    assert second.status_code == 201
    conflicting_update = updated_payload | {"reviewer": "other-reviewer"}
    assert client.put(f"/human-reviews/{review_id}", json=conflicting_update).status_code == 409

    reviews = client.get(f"/runs/{first_run['id']}/human-reviews")
    assert reviews.status_code == 200
    assert reviews.json()[0]["id"] in {review_id, second.json()["id"]}
    assert client.get(f"/human-reviews/{review_id}").status_code == 200
    assert client.get("/human-reviews/99999").status_code == 404
    assert len(client.get(f"/runs/{first_run['id']}/human-reviews?limit=1").json()) == 1
    assert client.get(f"/runs/{first_run['id']}/human-reviews?limit=0").status_code == 422


@pytest.mark.parametrize("score", [0.9, 5.1, float("nan"), float("inf")])
def test_human_review_rejects_invalid_scores(client: TestClient, score: float):
    from pydantic import ValidationError

    from app.schemas.human_review import HumanReviewCreate

    with pytest.raises(ValidationError):
        HumanReviewCreate.model_validate(review_payload(1, score=score))


def test_human_review_rejects_blank_reviewer(client: TestClient):
    run = client.post("/runs", json=sample_run()).json()
    evaluation_id = add_evaluation(run["id"], 3.0)
    response = client.post(
        f"/runs/{run['id']}/human-reviews",
        json=review_payload(evaluation_id) | {"reviewer": "   "},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("decision", ["adjust", "reject"])
def test_human_review_requires_notes_for_changed_decisions(client: TestClient, decision: str):
    run = client.post("/runs", json=sample_run()).json()
    evaluation_id = add_evaluation(run["id"], 3.0)
    payload = review_payload(evaluation_id) | {"review_decision": decision, "notes": "   "}
    assert client.post(f"/runs/{run['id']}/human-reviews", json=payload).status_code == 422


def test_calibration_uses_consensus_and_matches_golden_fixture(client: TestClient):
    runs = [
        client.post("/runs", json=sample_run(version)).json()
        for version in ("v1", "v2", "v3", "v4")
    ]
    evaluation_ids = [
        add_evaluation(runs[0]["id"], 4.0),
        add_evaluation(runs[1]["id"], 2.0),
        add_evaluation(runs[2]["id"], 4.5),
        add_evaluation(runs[3]["id"], 3.1),
    ]
    fixtures = (
        (0, "reviewer-a", 2.0, "agree"),
        (0, "reviewer-b", 4.0, "adjust"),
        (1, "reviewer-a", 3.0, "agree"),
        (2, "reviewer-a", 2.5, "reject"),
        (3, "reviewer-a", 2.6, "pending"),
    )
    for evaluation_index, reviewer, score, decision in fixtures:
        run = runs[evaluation_index]
        evaluation_id = evaluation_ids[evaluation_index]
        payload = review_payload(evaluation_id, reviewer, score) | {"review_decision": decision}
        assert client.post(f"/runs/{run['id']}/human-reviews", json=payload).status_code == 201

    response = client.get("/dashboard/calibration")
    assert response.status_code == 200
    data = response.json()
    assert data["review_count"] == 5
    assert data["calibrated_evaluation_count"] == 4
    assert data["reviewer_count"] == 2
    assert data["evaluation_coverage_rate"] == 1.0
    assert data["run_coverage_rate"] == 1.0
    assert data["overall_mae"] == 1.125
    assert data["overall_bias"] == 0.625
    assert data["overall_rmse"] == 1.25
    assert data["overall_agreement_rate"] == 0.25
    assert data["overall_large_disagreement_rate"] == 0.75
    assert data["acceptance_rate"] == 0.5
    assert data["decision_counts"] == {"pending": 1, "agree": 2, "adjust": 1, "reject": 1}

    overall = next(item for item in data["dimensions"] if item["dimension"] == "overall_score")
    assert overall["sample_count"] == 4
    assert overall["overrating_rate"] == 0.5
    assert overall["underrating_rate"] == 0.25
    for dimension in data["dimensions"]:
        assert dimension["sample_count"] == 4
        assert dimension["mae"] == 1.125
        assert dimension["bias"] == 0.625
        assert dimension["rmse"] == 1.25
        assert dimension["agreement_rate"] == 0.25
    assert data["disagreements"][0]["run_id"] == runs[2]["id"]
    assert data["disagreements"][0]["absolute_delta"] == 2.0
    assert data["disagreements"][0]["dangerous"] is True
    assert data["dangerous_samples"][0]["evaluation_id"] == evaluation_ids[2]


def test_empty_calibration_uses_null_metrics(client: TestClient):
    data = client.get("/dashboard/calibration").json()
    assert data["review_count"] == 0
    assert data["overall_mae"] is None
    assert data["overall_bias"] is None
    assert data["overall_correlation"] is None
    assert data["evaluation_coverage_rate"] is None
    assert data["run_coverage_rate"] is None
    assert data["disagreements"] == []
    assert data["dangerous_samples"] == []


def test_calibration_requires_and_isolates_model_rubric_scope(client: TestClient):
    first = client.post("/runs", json=sample_run("v1")).json()
    second = client.post("/runs", json=sample_run("v2")).json()
    first_evaluation = add_evaluation(first["id"], 4.0, "judge-a")
    second_evaluation = add_evaluation(second["id"], 2.0, "judge-b")
    assert client.post(
        f"/runs/{first['id']}/human-reviews",
        json=review_payload(first_evaluation, score=3.0),
    ).status_code == 201
    assert client.post(
        f"/runs/{second['id']}/human-reviews",
        json=review_payload(second_evaluation, score=4.0) | {"rubric_version": "research-report-v2"},
    ).status_code == 201

    assert client.get("/dashboard/calibration").status_code == 400
    scopes = client.get("/dashboard/calibration/scopes").json()
    assert {(item["evaluator_model"], item["rubric_version"]) for item in scopes} == {
        ("judge-a", "research-report-v1"), ("judge-b", "research-report-v2")
    }
    first_scope = client.get(
        "/dashboard/calibration?evaluator_model=judge-a&rubric_version=research-report-v1"
    ).json()
    second_scope = client.get(
        "/dashboard/calibration?evaluator_model=judge-b&rubric_version=research-report-v2"
    ).json()
    assert first_scope["review_count"] == first_scope["calibrated_evaluation_count"] == 1
    assert first_scope["overall_bias"] == 1.0
    assert second_scope["review_count"] == second_scope["calibrated_evaluation_count"] == 1
    assert second_scope["overall_bias"] == -2.0


def test_dangerous_samples_are_not_hidden_by_disagreement_limit(client: TestClient):
    for index in range(21):
        run = client.post("/runs", json=sample_run(f"ordinary-{index}")).json()
        evaluation_id = add_evaluation(run["id"], 5.0)
        assert client.post(
            f"/runs/{run['id']}/human-reviews",
            json=review_payload(evaluation_id, reviewer=f"reviewer-{index}", score=3.0),
        ).status_code == 201
    risky_run = client.post("/runs", json=sample_run("risky")).json()
    risky_evaluation = add_evaluation(risky_run["id"], 4.0)
    assert client.post(
        f"/runs/{risky_run['id']}/human-reviews",
        json=review_payload(risky_evaluation, reviewer="risk-reviewer", score=2.5),
    ).status_code == 201

    data = client.get("/dashboard/calibration").json()
    assert risky_evaluation not in {item["evaluation_id"] for item in data["disagreements"]}
    assert risky_evaluation in {item["evaluation_id"] for item in data["dangerous_samples"]}


def test_sqlite_foreign_keys_and_review_cascade_are_enforced(client: TestClient):
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    from app.models.evaluation import Evaluation
    from app.models.human_review import HumanReview

    with TestingSession() as db:
        assert db.scalar(text("PRAGMA foreign_keys")) == 1
        orphan = HumanReview(
            evaluation_id=99999, reviewer="orphan", review_decision="pending",
            rubric_version="research-report-v1", notes="", clarity_score=3,
            evidence_score=3, risk_coverage_score=3, specificity_score=3,
            actionability_score=3, novelty_score=3, overall_score=3,
        )
        db.add(orphan)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    run = client.post("/runs", json=sample_run()).json()
    evaluation_id = add_evaluation(run["id"], 3.0)
    with TestingSession() as db:
        invalid = HumanReview(
            evaluation_id=evaluation_id, reviewer="invalid", review_decision="bogus",
            rubric_version="research-report-v1", notes="", clarity_score=6,
            evidence_score=3, risk_coverage_score=3, specificity_score=3,
            actionability_score=3, novelty_score=3, overall_score=3,
        )
        db.add(invalid)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    review_id = client.post(
        f"/runs/{run['id']}/human-reviews", json=review_payload(evaluation_id)
    ).json()["id"]
    with TestingSession() as db:
        db.delete(db.get(Evaluation, evaluation_id))
        db.commit()
        assert db.get(HumanReview, review_id) is None


def test_review_queue_tracks_latest_unreviewed_evaluation(client: TestClient):
    run = client.post("/runs", json=sample_run()).json()
    first_evaluation = add_evaluation(run["id"], 2.0, "judge-old")
    latest_evaluation = add_evaluation(run["id"], 4.0, "judge-new")
    assert client.post(
        f"/runs/{run['id']}/human-reviews", json=review_payload(first_evaluation)
    ).status_code == 201
    queue = client.get("/human-review-queue").json()
    assert queue[0]["evaluation_id"] == latest_evaluation
    assert queue[0]["review_count"] == 0
    assert "overall_score" not in queue[0]
    assert "needs_human_review" not in queue[0]
    assert "evaluator_model" not in queue[0]


def test_existing_sqlite_database_adds_human_review_table_without_data_loss(tmp_path):
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.orm import Session

    from app.db import Base
    from app.models.evaluation import Evaluation
    from app.models.regression_case import RegressionCase
    from app.models.run import WorkflowRun

    upgrade_engine = create_engine(f"sqlite:///{tmp_path / 'upgrade.db'}")
    old_tables = [
        Base.metadata.tables[WorkflowRun.__tablename__],
        Base.metadata.tables[Evaluation.__tablename__],
        Base.metadata.tables[RegressionCase.__tablename__],
    ]
    Base.metadata.create_all(upgrade_engine, tables=old_tables)
    with Session(upgrade_engine) as db:
        run = WorkflowRun(**sample_run())
        db.add(run)
        db.commit()
        original_id = run.id

    Base.metadata.create_all(upgrade_engine)
    assert "human_reviews" in inspect(upgrade_engine).get_table_names()
    with Session(upgrade_engine) as db:
        assert db.get(WorkflowRun, original_id).prompt_version == "v1"


def test_legacy_human_review_table_is_rebuilt_without_data_loss(tmp_path):
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.orm import Session

    from app.db import Base, migrate_sqlite_human_reviews
    from app.models.evaluation import Evaluation
    from app.models.human_review import HumanReview
    from app.models.run import WorkflowRun

    upgrade_engine = create_engine(f"sqlite:///{tmp_path / 'legacy-review.db'}")
    Base.metadata.create_all(upgrade_engine)
    with Session(upgrade_engine) as db:
        run = WorkflowRun(**sample_run())
        db.add(run); db.flush()
        evaluation = Evaluation(
            run_id=run.id, evaluator_type="mock", evaluator_model="mock-v1",
            clarity_score=3, evidence_score=3, risk_coverage_score=3,
            specificity_score=3, actionability_score=3, novelty_score=3,
            overall_score=3, comments="legacy fixture",
        )
        db.add(evaluation); db.commit()
        run_id, evaluation_id = run.id, evaluation.id
    with upgrade_engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE human_reviews")
        connection.exec_driver_sql("""
            CREATE TABLE human_reviews (
                id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL, evaluation_id INTEGER NOT NULL,
                reviewer VARCHAR(120) NOT NULL, review_decision VARCHAR(20) NOT NULL,
                rubric_version VARCHAR(80) NOT NULL, clarity_score FLOAT NOT NULL,
                evidence_score FLOAT NOT NULL, risk_coverage_score FLOAT NOT NULL,
                specificity_score FLOAT NOT NULL, actionability_score FLOAT NOT NULL,
                novelty_score FLOAT NOT NULL, overall_score FLOAT NOT NULL, notes TEXT NOT NULL,
                created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                UNIQUE (evaluation_id, reviewer)
            )
        """)
        connection.execute(text("""
            INSERT INTO human_reviews VALUES
            (1, :run_id, :evaluation_id, 'legacy-reviewer', 'agree', 'research-report-v1',
             3, 3, 3, 3, 3, 3, 3, 'preserve me', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """), {"run_id": run_id, "evaluation_id": evaluation_id})

    migrate_sqlite_human_reviews(upgrade_engine)
    columns = {column["name"] for column in inspect(upgrade_engine).get_columns("human_reviews")}
    assert "run_id" not in columns
    assert "scores_edited_after_reveal" in columns
    with Session(upgrade_engine) as db:
        review = db.get(HumanReview, 1)
        assert review.notes == "preserve me"
        assert review.run_id == run_id
        assert review.scores_edited_after_reveal is False
