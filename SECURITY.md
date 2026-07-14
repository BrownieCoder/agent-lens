# Security Policy

## Supported versions

Agent Lens is currently an alpha project. Security fixes are applied to the latest `main` branch and latest tagged alpha release.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use GitHub's private vulnerability reporting feature after the repository is published.

## Alpha security boundaries

The current release is intended for local development and trusted networks. It does not yet provide authentication, authorization, tenant isolation, encryption at rest, rate limiting, audit logs, or automatic redaction.

Do not expose the FastAPI or Vite development servers directly to the public internet. Do not ingest confidential reports or personal data without adding the controls required by your environment. Human-review labels are unverified local identifiers, and review notes may contain sensitive context; neither should be treated as an authenticated audit trail. API keys must be supplied through environment variables and must never be committed.
