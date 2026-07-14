# Changelog

All notable changes to Agent Lens are documented here. The project follows Semantic Versioning once it reaches a stable release.

## Unreleased

### Added

- Blind-first human ratings bound to exact evaluator results.
- Editable review decisions and notes using a versioned research-report rubric.
- Calibration metrics for MAE, RMSE, signed bias, agreement, disagreement, and correlation.
- Human-review queue and largest-disagreement drill-down.
- Calibration dashboard with exact human–model score comparisons.
- Eight synthetic human reviews in the seed dataset.
- Model-and-rubric scoped calibration, explicit evaluation coverage, and independently retained high-risk samples.
- Blind-score provenance, decision reset after score edits, review history, and draft protection before evaluator reruns.
- A score-free Blind review queue that avoids model-priority ordering and anchors the end-to-end blind workflow.

## [0.1.0-alpha] - 2026-07-12

### Added

- FastAPI run logging and SQLite persistence.
- Deterministic mock evaluation with structured quality scores and risk flags.
- OpenAI and DeepSeek evaluator provider boundaries.
- Prompt-version analytics, daily trends, ranked runs, and Markdown summaries.
- Regression case management with paired seed examples.
- React dashboard, run explorer, evaluation detail, Prompt comparison, and regression UI.
- CI, release documentation, security guidance, and reproducible local commands.

### Known limitations

- No authentication, authorization, multi-tenancy, or production deployment profile.
- SQLite schema changes are not yet managed by Alembic.
- Real-provider evaluation requires the user's API credentials and incurs provider charges.
- LLM-as-judge scores require calibration against human review before high-stakes use.
