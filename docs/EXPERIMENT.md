# Reproducible small experiment

This procedure separates software verification from provider integration and evidence that an evaluator agrees with real people. The supplied outputs are synthetic, hand-authored fixtures. Mock scores test the application flow; they cannot establish evaluation quality. No real provider call or real human review is included. Both remain **UNVERIFIED** until explicitly authorized and actually performed.

## Prepare the fixed fixture without accessing a database or network

From the repository root:

```bash
python3 scripts/verify_experiment.py --output /tmp/lens-experiment-new
```

Without `--api-url`, the command refuses an existing output directory and writes only a deterministic manifest, its SHA-256, and an empty human-record CSV. It does not send HTTP requests, read `.env`, modify a database, fabricate ratings, or call a model. Use `--split exploration` or `--split holdout` to generate just one split. The default `all` manifest is for fixture inspection, not combined execution.

The manifest contains four exploration input pairs and two holdout input pairs. Within each pair, input, workflow, source type, synthetic model and generation method stay fixed; only prompt version and the deliberately authored output differ. It preserves prompt text, input/prompt hashes, output and generation parameters. Token, USD cost and latency measurements are unknown, not zero. This is a controlled software fixture, not measured prompt improvement.

## Execute exploration in its own database

Dashboard comparisons and Markdown reports have date filters, not experiment/workflow filters. Therefore this procedure uses **separate databases**, including when both stages run on the same day. Do not import both splits into one database. Use one operator, with no other imports while the script runs. Record the full Git SHA, dependency lock hashes, OS, Python and Node versions alongside the evidence.

After `make setup`, start the exploration service in terminal 1 from the repository root:

```sh
LENS_EXPLORATION_DIR=$(mktemp -d /tmp/lens-exploration.XXXXXX)
DATABASE_URL="sqlite:///$LENS_EXPLORATION_DIR/exploration.sqlite" EVALUATOR_BACKEND=mock make dev
```

Do not seed it. In terminal 2, choose an unused evidence directory and execute:

```sh
backend/.venv/bin/python scripts/verify_experiment.py --split exploration --api-url http://127.0.0.1:8000 --output /tmp/lens-exploration-evidence-new
```

`--api-url` explicitly enables local writes. The script accepts only a loopback HTTP API root, does not follow redirects or environment proxies, refuses `--split all`, and refuses a target containing any runs or regression cases. It creates the four cases **before** their linked runs, imports eight runs with prompt hash, generation parameters, dataset/experiment labels, and explicitly requests only the mock evaluator. It never creates human ratings or calls a paid provider.

The script verifies four matched input pairs per prompt version, eight evaluated runs, zero missing provenance, exact case associations and an export from the same isolated population. It saves `manifest.json`, `manifest.sha256`, `id-mapping.json` (run/case/exact evaluation/model/rubric), `verification.json`, `evaluation-summary.md` and the blank human-record template. IDs are recorded incrementally; a failure exits nonzero and may leave partial synthetic records. Preserve that database and evidence for diagnosis, then use a new database/output path for another attempt. Nothing is deleted or overwritten automatically.

Open `http://127.0.0.1:5173` to inspect the exploration population. The other split is absent from this database and these artifacts. Unknown generation measurements remain unknown; mock overhead is not a provider bill.

## Freeze decisions, then execute holdout separately

Record the frozen prompt/rubric versions and exploration decisions before opening holdout results. Stop the exploration server with Ctrl-C and retain its database. In terminal 1 start a second fresh database:

```sh
LENS_HOLDOUT_DIR=$(mktemp -d /tmp/lens-holdout.XXXXXX)
DATABASE_URL="sqlite:///$LENS_HOLDOUT_DIR/holdout.sqlite" EVALUATOR_BACKEND=mock make dev
```

In terminal 2:

```sh
backend/.venv/bin/python scripts/verify_experiment.py --split holdout --api-url http://127.0.0.1:8000 --output /tmp/lens-holdout-evidence-new
```

This creates two cases and four linked/evaluated runs, verifies two matched pairs per version, and exports only holdout. Keep the two artifact directories separate; compare their explicit sample counts. Do not repeatedly tune on holdout or claim generalization from two pairs. The fixture's authored output remains a software exercise, not a real generation experiment.

## Real human evidence is a separate step

When a real consenting human operator is available, have that person score through the blind-review UI before seeing judge scores, and record which isolated database and exact evaluation IDs they reviewed. The UI uses the fixed `local-reviewer` slot; it is not a multi-person collection interface. Additional people require separately recorded reviewer labels through `POST /runs/{id}/human-reviews`, with the coordinator collecting independent scores before reveal. Reusing the UI slot edits the existing review and cannot create a new independent participant. Keep the private mapping from anonymous sample labels to IDs separately. The CSV is a blank template, not simulated participants. Local labels are not verified identities; this version promises presentation-level blinding, not permission isolation. Record metadata that compromises blinding.

Record initial scores before reveal and decisions afterward. Post-reveal edits retain provenance and do not count as independent blind evidence. Do not copy mock/model scores into human fields. Inspect calibration with exact evaluator model and judge/human rubric scopes, sample counts and coverage; missing and undefined metrics are not zero. Save the calibration API JSON separately if needed; the Markdown summary is a run/prompt report, not a calibration export. Regression cases are already linked during import; no unsupported post-import relinking step is required.

## Optional real provider phase requires separate authorization

Before calling a paid provider, obtain an explicit provider/model, allowed input dataset, maximum calls and USD budget. A configured key is not authorization. Record exact generation and judge models, prompt/rubric hashes, sampling parameters, timestamps, request counts including retries, token usage and pricing source/date. Unknown usage or cost must remain unknown. Send only authorized nonsensitive data. Run representative malformed, unavailable-provider and embedded-instruction tests with SDK stubs first.

The two supplied prompt versions cannot prove a real generation effect because their output is fixed text. A real comparison must generate each pair with the same authorized model/parameters and input, change only the prompt, preserve outputs and failures, and account for repeated runs. Analyze failure rate and cost separately from score. A provider smoke test proves connectivity/contract behavior only.

## Reporting limits

Report software checks, real provider integration and real human effectiveness as three separate statuses. With no budget or human participants, deliver the fixture and this procedure with the last two statuses **UNVERIFIED**. Small convenience samples, heuristic mock scoring, source-looking prose and correlation are not benchmarks, external fact verification or evidence of human agreement. The exploration set is for development; the held-out set is for a one-time check after freezing decisions.
