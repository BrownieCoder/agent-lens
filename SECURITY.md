# Security Policy

## Supported versions

Agent Lens is currently an alpha project. Security fixes are applied to the latest `main` branch and latest tagged alpha release.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use [GitHub's private vulnerability reporting form](https://github.com/BrownieCoder/agent-lens/security/advisories/new) to submit a confidential report.

## Alpha security boundaries

The supported candidate profile is one trusted local operator with loopback-bound services and non-sensitive data; direct LAN or public serving is unsupported. Authenticated SSH forwarding may provide remote access while services remain loopback-only. It does not yet provide authentication, authorization, tenant isolation, encryption at rest, rate limiting, audit logs, or automatic redaction.

Host/Origin checks, JSON-only writes and a 1 MiB body limit are defense in depth, not authentication. The standard launcher uses one worker and explicit 127.0.0.1 bindings. See [operations and recovery](docs/OPERATIONS.md).

Do not expose the FastAPI or Vite development servers directly to the public internet. Do not ingest confidential reports or personal data without adding the controls required by your environment. Human-review labels are unverified local identifiers, and review notes may contain sensitive context; neither should be treated as an authenticated audit trail. API keys must be supplied through environment variables and must never be committed.
