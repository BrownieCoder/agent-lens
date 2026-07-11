# Agent Lens v0.1.0-alpha

Agent Lens is an eval-first observability dashboard for report-generating LLM workflows. This first public alpha turns subjective Prompt iteration into a measurable loop across output quality, evidence, risks, cost, latency, and failures.

## Highlights

- Log workflow inputs, outputs, Prompt versions, model metadata, token usage, cost, latency, and errors.
- Evaluate reports across seven quality dimensions and six conservative review flags.
- Start locally with a deterministic Mock evaluator and no API key.
- Switch to validated OpenAI or DeepSeek LLM-as-judge providers.
- Compare Prompt versions and inspect quality, cost, latency, and failure trends.
- Preserve hard inputs as regression cases and compare paired `v1`/`v2` runs.
- Export Markdown evaluation summaries.
- Run the complete FastAPI + React stack locally with `make setup`, `make seed`, and `make dev`.

## Engineering quality

- Seven backend tests cover the vertical API and evaluator failure paths.
- GitHub Actions validates backend tests, Python compilation, frontend builds, and npm security audit.
- Route-level code splitting keeps the frontend entry bundle small.
- Security policy, contribution guide, release checklist, pinned dependencies, and MIT license are included.

## Alpha boundaries

This release is intended for local development and trusted networks. It does not yet include authentication, authorization, multi-tenancy, redaction, rate limiting, or database migrations. LLM-as-judge scores should be calibrated against human review before high-stakes use.

See the README for screenshots, architecture, quick start, and roadmap.
