"""Historical records stay readable; attempt counts measure represented events."""
import pytest

from app.models.evaluation import Evaluation
from app.models.evaluation_attempt import EvaluationAttempt
from app.models.human_review import HumanReview
from app.models.regression_case import RegressionCase
from app.models.run import WorkflowRun
from app.schemas.evaluation import EvaluationPayload, EvaluationRead
from app.schemas.human_review import HumanReviewPayload, HumanReviewRead
from app.schemas.regression_case import RegressionCaseCreate, RegressionCaseRead
from app.schemas.run import RunCreate, RunRead
from pydantic import ValidationError
from test_api import client, clean_database, sample_run, TestingSession


SCORES = dict.fromkeys(("clarity_score", "evidence_score", "risk_coverage_score", "specificity_score", "actionability_score", "novelty_score", "overall_score"), 3)
FLAGS = dict.fromkeys(("possible_hallucination", "too_generic", "missing_risks", "overconfident_language", "weak_evidence", "needs_human_review"), False)


@pytest.mark.parametrize("old,success,failed,pending", [
    (2, 0, 0, 0), (0, 2, 1, 1), (2, 1, 0, 0),
    (2, 0, 1, 0), (1, 0, 0, 1), (2, 2, 2, 2),
])
def test_attempt_count_is_recorded_attempts_plus_unrepresented_evaluations(client, old, success, failed, pending):
    run_id = client.post("/runs", json=sample_run()).json()["id"]
    with TestingSession() as db:
        for _ in range(old):
            db.add(Evaluation(run_id=run_id, comments="legacy success", **SCORES))
        for index in range(success):
            evaluation = Evaluation(run_id=run_id, comments="recorded success", **SCORES)
            db.add(evaluation)
            db.flush()
            db.add(EvaluationAttempt(run_id=run_id, request_id=f"success-{index}", backend="mock", status="success", evaluation_id=evaluation.id))
        for status, count in (("failed", failed), ("pending", pending)):
            for index in range(count):
                db.add(EvaluationAttempt(run_id=run_id, request_id=f"{status}-{index}", backend="mock", status=status))
        db.commit()
    expected = old + success + failed + pending
    for summary in (client.get("/dashboard/summary").json(), client.get("/dashboard/prompt-comparison").json()[0]):
        assert summary["evaluation_attempt_count"] == expected
        assert summary["failed_evaluation_attempt_count"] == failed
        assert summary["pending_evaluation_attempt_count"] == pending
    if success:
        replay = client.post(f"/runs/{run_id}/evaluate", json={"evaluator_type": "mock", "request_id": "success-0"})
        assert replay.status_code == 201
        assert client.get("/dashboard/summary").json()["evaluation_attempt_count"] == expected


@pytest.mark.parametrize("overrides", [
    {"output_text": ""}, {"output_text": "x" * 108000},
    {"workflow_name": " "}, {"source_type": "s" * 81},
    {"input_text": ""}, {"input_text": "x" * 100001},
    {"prompt_version": "p" * 121}, {"model_name": "m" * 121},
    {"provider": "p" * 81}, {"status": "cancelled"},
    {"error_message": "e" * 4001},
    {"token_input": 1000000001, "token_output": 1000000001, "estimated_cost": 1000000001.5, "latency_ms": 1000000001},
])
def test_baseline_run_values_are_read_losslessly_but_rejected_on_new_posts(client, overrides):
    payload = sample_run() | overrides
    with TestingSession() as db:
        run = WorkflowRun(**payload)
        db.add(run)
        db.commit()
        run_id = run.id
    # The baseline write schema accepted these inputs. Reading must not reapply
    # new write limits, trim text, reinterpret status, or truncate any content.
    for url in (f"/runs/{run_id}", "/runs"):
        response = client.get(url)
        assert response.status_code == 200
        actual = response.json()[0] if isinstance(response.json(), list) else response.json()
        for field, value in payload.items():
            assert actual[field] == value
    blind = client.get(f"/runs/{run_id}/blind").json()["run"]
    for field, value in payload.items():
        assert blind[field] == value
    assert client.post("/runs", json=payload).status_code == 422


@pytest.mark.parametrize("comments", ["", "   ", "c" * 8001], ids=["empty", "whitespace", "long"])
def test_historical_evaluation_comments_read_on_all_routes_without_relaxing_provider_contract(client, comments):
    run_id = client.post("/runs", json=sample_run()).json()["id"]
    with TestingSession() as db:
        db.add(Evaluation(run_id=run_id, comments=comments, **SCORES))
        db.commit()
    for url in (f"/runs/{run_id}/evaluation", f"/runs/{run_id}", "/runs", "/dashboard/ranked-runs"):
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        evaluation = data if "overall_score" in data else (data["best"][0] if "best" in data else data[0] if isinstance(data, list) else data)["evaluations"][0]
        assert evaluation["comments"] == comments
    with pytest.raises(ValidationError):
        EvaluationPayload.model_validate(SCORES | FLAGS | {"comments": comments})


@pytest.mark.parametrize("overrides", [
    {"name": ""}, {"name": "n" * 161}, {"input_text": ""},
    {"input_text": "x" * 100001}, {"expected_focus": ""},
    {"expected_focus": "f" * 100001}, {"notes": "n" * 4001},
])
def test_historical_regression_cases_remain_readable_with_new_write_limits_intact(client, overrides):
    payload = {"name": "case", "input_text": " input ", "expected_focus": " focus ", "notes": " notes "} | overrides
    with TestingSession() as db:
        case = RegressionCase(**payload)
        db.add(case)
        db.commit()
        case_id = case.id
        run = WorkflowRun(**sample_run(), regression_case_id=case_id)
        db.add(run)
        db.commit()
    for url in (f"/regression-cases/{case_id}", "/regression-cases"):
        response = client.get(url)
        assert response.status_code == 200
        actual = response.json()[0] if isinstance(response.json(), list) else response.json()
        for field, value in payload.items():
            assert actual[field] == value
    assert client.get(f"/regression-cases/{case_id}/runs").status_code == 200
    assert client.post("/regression-cases", json=payload).status_code == 422


def test_all_read_models_are_serializers_and_do_not_apply_write_normalization(client):
    # Audit every Read class that previously inherited a write payload. Field
    # coverage catches accidental omissions when future write fields are added.
    for read, write in ((RunRead, RunCreate), (EvaluationRead, EvaluationPayload),
                        (RegressionCaseRead, RegressionCaseCreate), (HumanReviewRead, HumanReviewPayload)):
        assert not issubclass(read, write)
        assert set(write.model_fields) <= set(read.model_fields)
    run_id = client.post("/runs", json=sample_run()).json()["id"]
    with TestingSession() as db:
        evaluation = Evaluation(run_id=run_id, comments="historical review", **SCORES)
        db.add(evaluation)
        db.flush()
        review = HumanReview(evaluation_id=evaluation.id, reviewer=" historical reviewer ",
                             rubric_version=" historical rubric ", notes=" original notes \n", **SCORES)
        db.add(review)
        db.commit()
        review_id = review.id
    response = client.get(f"/human-reviews/{review_id}")
    assert response.status_code == 200
    assert response.json()["reviewer"] == " historical reviewer "
    assert response.json()["rubric_version"] == " historical rubric "
    assert response.json()["notes"] == " original notes \n"
