# Reproducible small experiment

This procedure separates software verification from provider integration and evidence that an evaluator agrees with real people. The supplied outputs are synthetic, hand-authored fixtures. Mock scores test the application flow; they cannot establish evaluation quality. No real provider call or real human review is included. Both remain **UNVERIFIED** until explicitly authorized and actually performed.

## Prepare the fixed fixture without accessing a database or network

From the repository root:

```bash
python3 scripts/verify_experiment.py --output /tmp/lens-experiment-new
```

The command refuses an existing output directory. It writes a deterministic manifest, its SHA-256, and an empty human-record CSV. It does not send HTTP requests, read `.env`, modify a database, fabricate ratings, or call a model.

The manifest contains four exploration input pairs and two holdout input pairs. Within each pair, input, workflow, source type, synthetic model and generation method stay fixed; only prompt version and the deliberately authored output differ. It preserves prompt text, input/prompt hashes, output and generation parameters. Token, USD cost and latency measurements are unknown, not zero. This is a controlled software fixture, not measured prompt improvement.

## Execute locally and collect evidence

1. Start the application with a newly created disposable SQLite path and its documented loopback-only configuration. Do not seed or reuse a personal database. Record the full Git SHA, dependency lock hashes, operating system, Python and Node versions in an external evidence directory.
2. Import each manifest `run` using `POST /runs`, keeping the returned run ID beside its manifest row. Evaluate with `POST /runs/{id}/evaluate` and `{"evaluator_type":"mock"}`. Preserve the returned exact evaluation ID, evaluator model and rubric version. Keep explorer and holdout workflows separate in all filters. Unknown generation measurements remain unknown. Mock overhead is not a provider bill.
3. Compare the two prompt versions. Confirm four paired exploration inputs, the same source/model and explicit denominator. Keep holdout results unopened while changing the rubric or prompt. After freezing the prompt and rubric, run the two holdout pairs once and report them separately; do not claim generalization from two pairs.
4. Ask real consenting human reviewers to independently score the reports through the blind-review UI before revealing judge scores. The CSV is a blank evidence template, not a list of simulated participants. Keep the private mapping from anonymous sample labels to exact evaluation IDs separately. Local reviewer labels are not verified identities. Record any UI metadata that compromises blinding; this version promises presentation-level blinding, not permission isolation.
5. Record initial human scores before reveal and decisions after reveal. Preserve provenance when scores change after reveal. Such edits must not count as independent blind evidence. Do not copy mock/model scores into human fields. Export calibration with exact evaluator/rubric/workflow scopes, sample counts and coverage; missing and undefined values are not zero.
6. Save the holdout cases as regression cases, link the corresponding runs, and export the filtered report. Archive the manifest, ID mapping, reports and actual observations locally. Confirm exported filters, missing measurements and denominators match the UI/API.

## Optional real provider phase requires separate authorization

Before calling a paid provider, obtain an explicit provider/model, allowed input dataset, maximum calls and USD budget. A configured key is not authorization. Record exact generation and judge models, prompt/rubric hashes, sampling parameters, timestamps, request counts including retries, token usage and pricing source/date. Unknown usage or cost must remain unknown. Send only authorized nonsensitive data. Run representative malformed, unavailable-provider and embedded-instruction tests with SDK stubs first.

The two supplied prompt versions cannot prove a real generation effect because their output is fixed text. A real comparison must generate each pair with the same authorized model/parameters and input, change only the prompt, preserve outputs and failures, and account for repeated runs. Analyze failure rate and cost separately from score. A provider smoke test proves connectivity/contract behavior only.

## Reporting limits

Report software checks, real provider integration and real human effectiveness as three separate statuses. With no budget or human participants, deliver the fixture and this procedure with the last two statuses **UNVERIFIED**. Small convenience samples, heuristic mock scoring, source-looking prose and correlation are not benchmarks, external fact verification or evidence of human agreement. The exploration set is for development; the held-out set is for a one-time check after freezing decisions.
