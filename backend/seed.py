import random
from datetime import datetime, timedelta, timezone

from app.db import SessionLocal, init_db
from app.models.evaluation import Evaluation
from app.models.regression_case import RegressionCase
from app.models.run import WorkflowRun
from app.services.evaluator import MockEvaluator


SOURCES = ["discord", "tweetshift", "analyst_note", "manual"]
INPUTS = [
    "Company reported quarterly revenue growth and raised guidance after stronger enterprise demand.",
    "Market discussion claims a major partnership is imminent, but no primary source is linked.",
    "Analyst note highlights margin pressure, inventory changes, and a possible second-half recovery.",
    "Social posts report unusual volume following a regulatory filing and management commentary.",
]


def report_text(index: int, version: str) -> str:
    if version == "v1":
        return (
            "The update is positive and worth watching. The company appears well positioned, "
            "although investors should remain careful. In conclusion, this could be important."
        )
    growth = 8 + index % 13
    return (
        f"Signal: reported demand implies approximately {growth}% year-over-year growth, according to the supplied source.\n\n"
        "Evidence: the input mentions guidance and operating indicators, but it does not provide a primary filing link; "
        "the claim should be verified before use.\n\n"
        "Risks: downside includes weaker conversion, margin pressure, source reliability, and uncertain timing.\n\n"
        "Next action: monitor the next filing, compare guidance with consensus, and watch for confirmation from management."
    )


def main() -> None:
    random.seed(7)
    init_db()
    with SessionLocal() as db:
        if db.query(WorkflowRun).count():
            print("Seed skipped: workflow_runs already contains data.")
            return
        evaluator = MockEvaluator()
        cases = []
        for case_index in range(12):
            case = RegressionCase(
                name=f"X-signal benchmark {case_index + 1:02d}",
                input_text=INPUTS[case_index % len(INPUTS)],
                expected_focus=(
                    "Separate supplied facts from inference; identify source reliability, quantify specific signals, "
                    "cover downside risks, and give a concrete verification action."
                ),
                notes="Seeded benchmark; compare v1 and v2 runs linked to this case.",
            )
            db.add(case)
            cases.append(case)
        db.flush()
        for index in range(24):
            version = "v1" if index < 12 else "v2"
            failed = index in (3, 17)
            run = WorkflowRun(
                workflow_name="x-signal-agent",
                source_type=SOURCES[index % len(SOURCES)],
                input_text=INPUTS[index % len(INPUTS)],
                output_text="" if failed else report_text(index, version),
                prompt_version=version,
                model_name="gpt-4.1-mini",
                provider="openai",
                token_input=700 + index * 11,
                token_output=0 if failed else (230 if version == "v1" else 480),
                estimated_cost=round(0.0012 + index * 0.00008 + (0.001 if version == "v2" else 0), 6),
                latency_ms=900 + index * 47 + (400 if version == "v2" else 0),
                status="error" if failed else "success",
                error_message="Upstream provider timeout" if failed else None,
                regression_case_id=cases[index % 12].id,
                created_at=datetime.now(timezone.utc) - timedelta(days=23 - index),
            )
            db.add(run)
            db.flush()
            result = evaluator.evaluate(run)
            db.add(Evaluation(
                run_id=run.id,
                evaluator_type=result.evaluator_type,
                evaluator_model=result.evaluator_model,
                **result.payload.model_dump(),
            ))
        db.commit()
        print("Created 12 regression cases and 24 paired sample runs with mock evaluations.")


if __name__ == "__main__":
    main()
