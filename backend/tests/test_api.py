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
