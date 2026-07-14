# Agent Lens

[English](README.md) · [简体中文](README.zh-CN.md)

> Early alpha. A small, self-hosted dashboard for evaluating report-generating LLM workflows.

[![CI](https://github.com/BrownieCoder/agent-lens/actions/workflows/ci.yml/badge.svg)](https://github.com/BrownieCoder/agent-lens/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Release: alpha](https://img.shields.io/badge/release-v0.1.0--alpha-orange.svg)](https://github.com/BrownieCoder/agent-lens/releases/tag/v0.1.0-alpha)

I built Agent Lens to answer a recurring question in my own workflow: after changing a prompt or model, did the report actually improve? The app records runs, scores them against a fixed rubric, and compares quality alongside cost, latency, and failures.

![Agent Lens dashboard](docs/assets/dashboard.png)

## Background

The first version grew out of an `x-signal-agent` experiment that turns market signals into short research notes. Looking at traces was useful for debugging, but it did not help me decide whether one prompt produced better research than another. I wanted a local tool with a deliberately narrow loop:

```text
output → evaluation → comparison → prompt change
```

The sample data still reflects that original financial-research use case. The storage and API layers do not depend on it, so other report-style workflows can use the same run and evaluation model.

## What works today

- Store workflow inputs, outputs, model metadata, token usage, cost, latency, and errors.
- Score reports across seven dimensions and flag six common review risks.
- Run evaluations offline with the deterministic mock evaluator, or use OpenAI and DeepSeek.
- Compare prompt versions and keep difficult inputs as regression cases.
- Add blind human ratings tied to exact evaluator results and measure judge calibration.
- Export a Markdown evaluation summary for experiment notes.

## Demo

`make seed` creates 24 runs against 12 paired cases and adds eight synthetic human reviews. The `v1` outputs are intentionally vague; `v2` adds evidence, risks, and a next action. This makes the comparison and calibration screens useful immediately, without spending API credits.

## Quick start

Requirements: Python 3.11+, Node.js 20+, and `make`.

```bash
git clone https://github.com/BrownieCoder/agent-lens.git
cd agent-lens
make setup
cp .env.example backend/.env
make seed
make dev
```

Open:

- Dashboard: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

`make dev` runs the backend and frontend together. You can also run `make backend` and `make frontend` in separate terminals.

## Evaluators

The default is `mock`, so a fresh clone works without credentials.

| Backend | Key required | Output contract | Intended use |
|---|---|---|---|
| `mock` | No | Deterministic Pydantic payload | Local demo, tests, offline development |
| `openai` | `OPENAI_API_KEY` | Strict JSON Schema | Hosted evaluator |
| `deepseek` | `DEEPSEEK_API_KEY` | JSON mode + Pydantic validation | Hosted evaluator |

Configure the default in `backend/.env`:

```dotenv
EVALUATOR_BACKEND=deepseek
DEEPSEEK_API_KEY=your_key
DEEPSEEK_EVALUATOR_MODEL=deepseek-v4-flash
```

Or override it for one request:

```bash
curl -X POST http://localhost:8000/runs/1/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"evaluator_type":"deepseek"}'
```

Provider calls incur provider charges. Model-produced JSON is always validated before persistence; malformed or empty provider output returns HTTP `502` instead of being stored.

To make one real provider request with synthetic input, without starting the app or writing to its database:

```bash
make smoke-provider                   # DeepSeek
make smoke-provider PROVIDER=openai   # OpenAI
```

The command reads the corresponding key from `backend/.env`, prints only the provider, model, score, review flag, and schema status, and exits non-zero if the provider response is invalid.

## Human review and calibration

Start human judgment from the dedicated **Blind review** queue. It deliberately omits evaluator scores, flags, rankings, and model-priority sorting; the general Runs and analytics pages are not blind entry points. On the run page, Agent Lens then hides the model score until the first human rating is saved. The review is bound to that exact `evaluation_id`, so rerunning an evaluator cannot silently change the calibration pair. After the blind rating, the reviewer can compare scores and accept, adjust, or reject the model assessment.

The Calibration page aggregates one human consensus per evaluation. It defines signed error as `model − human` and reports:

- MAE and RMSE for absolute error magnitude.
- Bias, where a positive value means the evaluator scores higher than people.
- Agreement rate for an absolute score gap of 0.5 or less.
- Large-disagreement rate for an absolute gap of 1.0 or more.
- Pearson correlation when at least two non-constant pairs exist.
- High-risk cases where evaluator overall is at least 4.0 and human consensus is at most 2.5.

Human ratings are calibration evidence, not automatic ground truth. Multiple reviews of one evaluation are averaged before that evaluation enters aggregate metrics, preventing heavily reviewed samples from receiving extra weight.

Calibration is always scoped to one `evaluator_model` and one `rubric_version`; incompatible judge or rubric populations are never averaged together. Evaluation coverage counts reviewed evaluator results over all evaluator results in that model scope. The acceptance rate is reviewer-level: `agree / (agree + adjust + reject)`, excluding pending reviews. Editing a score after model reveal resets its decision to pending and records that provenance.

## Architecture

```mermaid
flowchart LR
    W["LLM workflow"] -->|POST /runs| A["FastAPI"]
    A --> D[("SQLite / SQLAlchemy")]
    A --> E{"Evaluator"}
    E --> M["Mock"]
    E --> O["OpenAI"]
    E --> DS["DeepSeek"]
    M --> D
    O --> D
    DS --> D
    H["Human review"] --> D
    D --> X["Analytics & reports"]
    X --> R["React dashboard"]
```

```text
backend/app/
  models/       Run, evaluation, human-review, and regression entities
  routers/      Run, evaluation, human-review, dashboard, regression, and report APIs
  services/     Evaluators, calibration, analytics, and Markdown export
  schemas/      Validated request and response contracts
frontend/src/
  pages/        Dashboard, runs, prompt comparison, regression, calibration
  components/   Score cards, charts, tables, evaluation and human-review panels
```

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/runs` | Log a workflow run |
| GET | `/runs` | Filter and list runs |
| GET | `/runs/{id}` | Inspect a run and its evaluations |
| POST | `/runs/{id}/evaluate` | Run Mock, OpenAI, or DeepSeek evaluation |
| GET | `/runs/{id}/evaluation` | Fetch the latest evaluation |
| POST/GET | `/runs/{id}/human-reviews` | Create or list reviews bound to an evaluation |
| GET/PUT | `/human-reviews/{id}` | Read or update one human review |
| GET | `/human-review-queue` | List latest evaluations waiting for review |
| GET | `/dashboard/summary` | Aggregate KPI summary |
| GET | `/dashboard/trends` | Daily quality, cost, and latency trends |
| GET | `/dashboard/prompt-comparison` | Compare prompt versions |
| GET | `/dashboard/ranked-runs` | Find best and worst runs |
| GET | `/dashboard/calibration` | Compare evaluator scores with human consensus |
| GET | `/dashboard/calibration/scopes` | List available evaluator-model and rubric scopes |
| POST/GET | `/regression-cases` | Create or list regression cases |
| GET | `/regression-cases/{id}/runs` | Compare runs linked to one case |
| POST | `/reports/evaluation-summary` | Export a Markdown summary |

## Verification

```bash
make check
```

This runs backend tests, Python compilation, the frontend build, and the npm audit. CI runs the same checks on pushes and pull requests.

## Current boundaries

This alpha release is designed for local development and trusted networks. It does not yet include authentication, authorization, multi-tenancy, redaction, rate limiting, or schema migrations. Reviewer labels are local identifiers rather than verified identities, and review notes may contain sensitive context. Do not expose the development servers publicly or ingest confidential data without adding the controls required by your environment. See [SECURITY.md](SECURITY.md).

LLM-as-judge output is a signal, not ground truth. Calibrate scoring against human review before using it for high-stakes decisions.

## Roadmap

- Pairwise output comparison
- Dataset and experiment versioning
- Alembic migrations and Postgres production profile
- OpenTelemetry trace ingestion
- CI quality gates for Prompt regressions

See [PLAN.md](PLAN.md) for implementation notes and open questions.

## Project notes

- Contributions: [CONTRIBUTING.md](CONTRIBUTING.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md)
- Release checklist: [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md)
- License: [MIT](LICENSE)
