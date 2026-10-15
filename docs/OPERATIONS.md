# Local installation, upgrade and recovery

Supported profile: one trusted operator, macOS/Linux, Python 3.11+, Node.js 20+, `make`, a local SQLite file, one backend worker. Use non-sensitive or synthetic reports. The HTTP API has no user authentication. Native Windows is not supported by the POSIX process-group launcher; use a Linux environment. Do not bind to a LAN/public interface. No multi-tenant or high-concurrency guarantee is made.

## Install and run

From a clean checkout of the reviewed candidate:

```sh
make setup
cp .env.example backend/.env
make dev
```

`make setup` uses exact direct/transitive Python versions in `backend/requirements.lock` and `npm ci` with the frontend lock. Dependency installation requires registry access. No hosted evaluator is required; `mock` is the default. Keep environment files outside version control. Never copy a developer's database into a demo checkout.

The launcher explicitly binds API `127.0.0.1:8000` and Vite `127.0.0.1:5173`, with one API worker and fixed ports. Open `http://127.0.0.1:5173`. `GET http://127.0.0.1:8000/health` verifies a database connection. API documentation is at `/docs`. Ctrl-C stops both service process groups; a port/startup failure stops its sibling. `make backend` and `make frontend` are available for separate terminals. Vite preview alone is not a supported full-app server because it does not proxy the API.

For remote operation, keep both processes loopback-bound on the remote host and use authenticated SSH:

```sh
ssh -N -L 5173:127.0.0.1:5173 -L 8000:127.0.0.1:8000 operator@your-host
```

SSH account access is the remote access boundary; direct shared-network HTTP serving is unsupported. Use existing organization-approved SSH authentication. The app rejects non-loopback Host names and unlisted browser Origins, requires JSON writes, and bounds write bodies to 1 MiB. These guards are not authentication or protection from another trusted local OS user. Do not set a public host or wildcard CORS origin. No encryption at rest, account isolation, audit logging or automatic redaction is provided.

## First use and checks

`make seed` is optional, synthetic only. It skips a workspace containing any business data. For an empty real workspace, omit seed and log runs with `POST /runs`; then evaluate, use Blind review, compare prompts, inspect Calibration, save Regression cases, and use Overview's **Export displayed summary**. Date filters use UTC run creation dates and the export uses the applied range, not unapplied form edits.

```sh
make check
python3 scripts/verify_experiment.py --help
```

Checks use mocked provider behavior. Real provider smoke is a separate, explicitly authorized paid operation; it does not establish judge reliability. See [EXPERIMENT.md](EXPERIMENT.md). Dependency audit requires network access and may reveal newly published advisories even if older CI was green.

## Backup, upgrade and rollback

Before upgrading, stop both services, record the installed commit (`git rev-parse HEAD`), and record the configured database path without copying credentials into logs. The default path is `backend/agent_lens.db`. The snapshot command uses SQLite's backup API and validates integrity/foreign keys; it never overwrites an existing destination.

```sh
python3 scripts/database_snapshot.py backup backend/agent_lens.db /safe/local/path/pre-upgrade.sqlite
```

Keep the snapshot on trusted local storage with appropriate permissions. This tool does not encrypt it. Review content is private application data, not a CI artifact.

After taking a snapshot, checkout the reviewed version, run `make setup`, then `make dev`. Supported prior alpha schemas are upgraded during startup; exact review bindings and original records must remain intact. A failed migration must fail startup and roll back changes. Unknown or invalid legacy data must be investigated against a preserved snapshot; do not delete tables or edit a failed database to force startup. Do not run multiple workers during migration.

Verify health and a known run/evaluation/review, run checks on a separate synthetic database, and keep the original snapshot until acceptance. Restoring the backup into a *new* path is also the rollback path:

```sh
python3 scripts/database_snapshot.py restore /safe/local/path/pre-upgrade.sqlite /safe/local/path/restored.sqlite
```

Stop the candidate, checkout the recorded old commit, reinstall its dependencies, and launch it with `DATABASE_URL=sqlite:////safe/local/path/restored.sqlite make dev`. Keep the failed/new database for diagnosis; do not point the old binary at a schema upgraded by newer code. Recovery does not undo external provider charges. No automatic downgrade of upgraded schemas is promised.

## Troubleshooting and limits

- Port in use: stop the conflicting local service or use a separate test checkout with explicitly coordinated frontend/backend ports; the standard launcher does not silently choose another frontend port.
- Invalid CORS/evaluator config: fix the named configuration field using `.env.example`; never paste the entire environment into issue reports.
- Missing provider key: the selected hosted evaluator fails explicitly; use mock for offline checks. Provider timeouts/rate limits/auth/invalid output are failures, not zero-quality successful evaluations. An ambiguous timed-out request may still be billed by a provider.
- SQLite locked: stop concurrent writers and run a single worker; preserve the database and inspect the process that holds it. Do not remove the file.
- Dependency install/audit network failure: this is UNVERIFIED, not a passing audit. Retry with registry access and preserve the actual exit status.
- No retention service exists. Exporting Markdown intentionally includes derived report metrics and user-supplied labels; inspect before sharing. Do not use confidential data without adding and verifying the controls your environment requires.
