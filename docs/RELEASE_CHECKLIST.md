# Release candidate checklist

Start a new external evidence record for each candidate. These boxes are intentionally unclaimed; historical alpha releases are not evidence for a new SHA. See [acceptance contract](ACCEPTANCE_CONTRACT.md) and [review workflow](DELIVERY_WORKFLOW.md).

- [ ] Record full local/remote head, base, branch, frozen contract hash and clean source status.
- [ ] Fresh locked install, start/stop, health, offline mock and empty database verified.
- [ ] Backend tests, frontend build, compile and network dependency audit actually pass; exact candidate CI jobs executed.
- [ ] Browser record/evaluate/compare/blind-score/reveal/decision/edit/calibration/history/regression/export workflow verified with synthetic data, plus pagination/search/date/error/refresh checks.
- [ ] Independent golden metrics, strict provider error matrix, duplicate-call protection, safe migration failure, persistence, backup and restore verified.
- [ ] README in both languages, configuration, API schema, operations/rollback, changelog and limitations agree with code.
- [ ] Both fresh reviewers' immutable initial and reconciliation reports bind exact SHA/base/contract; all critical historical findings closed; no unaccepted P2.
- [ ] Live provider connectivity and real human-effectiveness evidence reported separately; absence marked UNVERIFIED, never replaced by synthetic reviews.
- [ ] Reports/screenshots contain synthetic data only and no secrets.
- [ ] Human separately authorizes merge, release/tag and deployment. Never publish based only on a green CI badge.

Repository permissions/branch protections must be inspected before claiming enforcement. The review workflow is a manual process gate unless protected infrastructure independently attests it; candidate code cannot approve itself. No repository-management changes are implied by this checklist.
