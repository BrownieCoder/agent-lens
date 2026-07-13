# Release checklist

## Repository

- [x] Replace placeholder repository URLs after publishing.
- [x] Confirm MIT license owner and year (`Wayne Zheng`, 2026).
- [x] Enable GitHub private vulnerability reporting.
- [x] Enable branch protection and require the CI workflow.
- [x] Add repository description and topics.
- [ ] Add a repository social preview image.

## Quality

- [x] `make check` passes locally with pinned dependencies.
- [x] `make seed` creates 12 cases and 24 paired runs in an isolated database.
- [x] Dashboard, run detail, Prompt comparison, regression, and 404 pages pass browser smoke tests.
- [x] Mock evaluator works without credentials.
- [ ] OpenAI and DeepSeek provider calls are tested with the maintainer's own credentials.

## Release

- [x] Move `0.1.0-alpha` changelog entry from Unreleased to the release date.
- [x] Create tag `v0.1.0-alpha` from `main`.
- [x] Create a GitHub pre-release using the changelog notes.
- [x] Verify `make setup`, `make seed`, and `make check` from a fresh public clone.
- [x] Share only synthetic screenshots and example data.

Authenticated repository setup is documented in [GITHUB_RELEASE_SETUP.md](GITHUB_RELEASE_SETUP.md).
