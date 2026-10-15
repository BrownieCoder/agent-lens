"""Independent arithmetic oracles; every database contains synthetic fixtures only."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models.evaluation import Evaluation
from app.models.human_review import HumanReview
from app.models.run import WorkflowRun
from app.services.calibration import calibration_data


DIMENSIONS = (
    "clarity_score", "evidence_score", "risk_coverage_score", "specificity_score",
    "actionability_score", "novelty_score", "overall_score",
)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def add_pair(db, judge, humans, *, run=None, model="qa-judge", rubric="research-report-v1"):
    if run is None:
        run = WorkflowRun(workflow_name="qa", source_type="synthetic", input_text="fixed input",
                          output_text="fixed report", prompt_version="v1", model_name="fixture")
        db.add(run)
        db.flush()
    evaluation = Evaluation(run_id=run.id, evaluator_type="mock", evaluator_model=model,
                            **dict.fromkeys(DIMENSIONS, judge))
    db.add(evaluation)
    db.flush()
    for index, (human, decision) in enumerate(humans):
        db.add(HumanReview(evaluation_id=evaluation.id, reviewer=f"synthetic-{index}",
                           rubric_version=rubric, review_decision=decision,
                           **dict.fromkeys(DIMENSIONS, human)))
    db.commit()
    return run, evaluation


def test_hand_calculated_consensus_equal_weight_and_missing_coverage(db):
    # Judge [1,3,5], human consensus [2,2,4]. Errors [-1,1,1].
    # MAE=RMSE=1; bias=1/3; Pearson=4/sqrt(8*(8/3))=sqrt(3)/2.
    # A heavily reviewed first item must not receive extra metric weight.
    run, _ = add_pair(db, 1, [(1, "agree"), (2, "agree"), (3, "adjust")])
    add_pair(db, 3, [(2, "reject")])
    add_pair(db, 5, [(4, "pending")])
    add_pair(db, 4, [], run=run)  # Older and newer evaluations stay distinct.
    result = calibration_data(db, evaluator_model="qa-judge", rubric_version="research-report-v1")
    assert result["overall_mae"] == 1
    assert result["overall_rmse"] == 1
    assert result["overall_bias"] == 0.333
    assert result["overall_correlation"] == 0.866
    assert result["overall_agreement_rate"] == 0
    assert result["overall_large_disagreement_rate"] == 1
    assert result["review_count"] == 5
    assert result["calibrated_evaluation_count"] == 3
    assert result["evaluated_evaluation_count"] == 4
    assert result["evaluation_coverage_rate"] == 0.75
    assert result["run_coverage_rate"] == 1
    assert result["acceptance_rate"] == 0.5  # 2 agree / 4 non-pending decisions.
    for dimension in result["dimensions"]:
        assert dimension["sample_count"] == 3
        assert dimension["mae"] == dimension["rmse"] == 1
        assert dimension["overrating_rate"] == 0.667
        assert dimension["underrating_rate"] == 0.333


@pytest.mark.parametrize("pairs,correlation", [
    ([(1, 1)], None), ([(3, 1), (3, 5)], None),
    ([(1, 3), (5, 3)], None), ([(1, 5), (5, 1)], -1),
    ([(1, 1), (5, 5)], 1),
])
def test_correlation_undefined_and_endpoint_cases(db, pairs, correlation):
    for judge, human in pairs:
        add_pair(db, judge, [(human, "pending")])
    result = calibration_data(db)
    assert result["overall_correlation"] == correlation
    assert result["acceptance_rate"] is None


def test_agreement_thresholds_are_inclusive(db):
    for judge, human in [(3, 2.5), (2, 2.5), (4, 3), (2, 3)]:
        add_pair(db, judge, [(human, "pending")])
    result = calibration_data(db)
    assert result["overall_agreement_rate"] == 0.5
    assert result["overall_large_disagreement_rate"] == 0.5
    assert result["overall_mae"] == 0.75
    assert result["overall_rmse"] == 0.791  # sqrt((.25+.25+1+1)/4)
    assert result["overall_bias"] == 0


def test_revealed_score_edits_do_not_become_independent_calibration(db):
    _, evaluation = add_pair(db, 5, [(1, "pending")])
    review = db.query(HumanReview).filter_by(evaluation_id=evaluation.id).one()
    review.scores_edited_after_reveal = True
    for dimension in DIMENSIONS:
        setattr(review, dimension, 5)
    db.commit()
    result = calibration_data(db)
    # No original-score snapshot exists on the legacy row. Excluding the row is
    # necessary; treating its revealed perfect match as blind evidence is false.
    assert result["calibrated_evaluation_count"] == 0
    assert result["overall_mae"] is None


def test_model_and_rubric_scope_excludes_other_consensus(db):
    add_pair(db, 5, [(1, "pending")], model="judge-a", rubric="rubric-a")
    add_pair(db, 1, [(5, "pending")], model="judge-b", rubric="rubric-b")
    result = calibration_data(db, evaluator_model="judge-a", rubric_version="rubric-a")
    assert result["review_count"] == result["evaluated_evaluation_count"] == 1
    assert result["overall_bias"] == 4
