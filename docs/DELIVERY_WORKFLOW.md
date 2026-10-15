# Release delivery workflow

The frozen [acceptance contract](ACCEPTANCE_CONTRACT.md) defines the supported deployment and required evidence. Freeze its version/hash before review; changes to scope or base require renewed verification.

Five responsibilities remain distinct: delivery lead/architect, implementation engineer, QA/evaluation/release engineer, independent reviewer A, and independent reviewer B. The first three may retain context. Reviewers may not implement the candidate. Limited execution slots require staggered scheduling, with the limitation recorded; never invent additional identities.

1. Record clean/dirty state, local and remote full SHA, base, branch, open PR, release, runtime versions and actual baseline checks. Preserve unrelated changes. Review the baseline globally.
2. Implement a coherent batch with independent regression expectations. Use separate checkouts/branches and file ownership for parallel writes. Integrate sequentially. Run relevant tests/build plus `make check` for broad delivery changes.
3. Commit, push only the task branch, then obtain the full remote SHA. Create a fresh pair of isolated reviewers for **every push**, including docs/config/dependency-only changes. Each reviews the entire pushed range and global acceptance. Never resume a previous reviewer or inherit implementation history.
4. Supply identical neutral inputs: project goal, frozen contract, permissions, head/base SHAs, source and cumulative diff, formal product docs, and environment/test instructions. Do not supply author self-assessment, earlier approvals, previous review findings or the peer's results initially.
5. Each reviewer independently saves an immutable first report. Only after both are saved, provide the shared unresolved/historical findings ledger and relevant explanations; each appends a reconciliation report. Retain original reports.
6. Confirm checks actually ran and passed on the applicable SHA. Pending, skipped, cancelled, absent and stale results are not passing evidence. Fix confirmed defects, retest, commit/push and restart with a new pair. A moving remote HEAD invalidates the prior approval.
7. Hand off only when the exact final SHA satisfies all required gates, both independent verdicts are PASS and all critical historical findings are verified closed. Merge/release/deploy require separate human authorization; a resulting new SHA cannot reuse old approval without verifying applicable gates.

Review A emphasizes correctness, integrity and security; B emphasizes product workflows, evaluation trust and reproducibility. **Both review the full contract.** Review findings require severity P0–P3, SHA, location, expected/actual behavior, reproduction/evidence, impact, suggested verification and status. P0/P1 must close. P2 deferrals require explicit named human acceptance, impact and follow-up. Conflicting conclusions are resolved by evidence, not a majority vote.

Store reports and a round ledger outside the reviewed branch (local evidence directory or sanitized PR/CI artifacts). Record before/after push SHAs, branch/base/contract hash, actual session identifiers and exposed model identifiers, isolation details, immutable report paths, executed checks/CI URLs, issue status and final state. Do not create a new commit merely to claim approval of the previous SHA.

Reviewer report fields:

```yaml
reviewer_role:
session_id:
model:
head_sha:
base_sha:
acceptance_contract_version:
fresh_context_setup:
possible_context_exposure:
inspected_scope:
checks_actually_run:
evidence_locations:
findings:
remaining_unknowns:
historical_findings_verification:
verdict: PASS | CHANGES_REQUIRED | UNVERIFIED
verdict_reason:
remaining_risks:
```

Unavailable runtime identifiers must be marked unavailable; role names are not proof of unique model identities. If cold sessions cannot be created, record `INDEPENDENT_REVIEW_BLOCKED`, prepare two neutral task packages, and continue other work without asserting approval. If independent reports cannot be authenticated by protected infrastructure, this remains a **manual process gate**, not enforced repository protection. Two comments from one account are not two native approvals. A format validator cannot attest that review occurred.

Software readiness, live provider connectivity, and effectiveness demonstrated by real independent human ratings are three separate conclusions. Report each honestly; synthetic scores are never human evidence. Final state: `READY FOR HUMAN MERGE / RELEASE APPROVAL`, `CHANGES REQUIRED`, or `BLOCKED / UNVERIFIED`.
