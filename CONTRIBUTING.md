# Contributing to Agent Lens

Agent Lens is an early-stage project. Focused bug fixes, evaluator improvements, provider integrations, and workflow examples are welcome.

## Development setup

```bash
make setup
make seed
make dev
```

The frontend runs at `http://localhost:5173` and the API at `http://localhost:8000`.

## Before opening a pull request

```bash
make check
```

Please keep changes scoped, include tests for backend behavior, and update `README.md` or `PLAN.md` when behavior or project direction changes. Never commit API keys, real financial reports, personal data, generated databases, or provider responses containing sensitive information.

## Pull requests

- Explain the user problem and the chosen trade-off.
- Include screenshots for visible UI changes.
- Note schema or environment-variable changes explicitly.
- Keep evaluator behavior conservative and validate all model-produced JSON.
