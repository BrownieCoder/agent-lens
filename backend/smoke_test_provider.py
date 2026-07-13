"""Make one real evaluator request without writing application data."""

import argparse

from app.config import Settings
from app.models.run import WorkflowRun
from app.services.evaluator import ProviderEvaluationError, get_evaluator


def sample_run() -> WorkflowRun:
    return WorkflowRun(
        workflow_name="provider-smoke-test",
        source_type="manual",
        input_text=(
            "The quarterly filing reports 12% year-over-year revenue growth. "
            "Management raised guidance, while gross margin fell by 1.5 percentage points."
        ),
        output_text=(
            "Revenue grew 12% year over year according to the quarterly filing, and management "
            "raised guidance. The signal is constructive, but the 1.5 percentage-point gross "
            "margin decline may limit earnings upside. Verify the guidance change in the filing "
            "and compare next-quarter margins before acting."
        ),
        prompt_version="smoke-test-v1",
        model_name="fixture",
        provider="local",
        status="success",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send one synthetic report to a hosted Agent Lens evaluator."
    )
    parser.add_argument("--provider", choices=("deepseek", "openai"), default="deepseek")
    args = parser.parse_args()

    settings = Settings()
    try:
        result = get_evaluator(args.provider, settings).evaluate(sample_run())
    except (ValueError, ProviderEvaluationError) as exc:
        print(f"Smoke test failed: {exc}")
        return 1

    payload = result.payload
    print(f"Provider: {args.provider}")
    print(f"Model: {result.evaluator_model}")
    print(f"Overall score: {payload.overall_score:.1f}/5")
    print(f"Needs human review: {payload.needs_human_review}")
    print("Response schema: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
