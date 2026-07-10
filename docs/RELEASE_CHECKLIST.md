# Release checklist

## Repository

- [ ] Replace placeholder repository URLs after publishing.
- [ ] Confirm MIT license owner and year.
- [ ] Enable GitHub private vulnerability reporting.
- [ ] Enable branch protection and require the CI workflow.
- [ ] Add repository description, topics, and social preview.

## Quality

- [x] `make check` passes locally with pinned dependencies.
- [x] `make seed` creates 12 cases and 24 paired runs in an isolated database.
- [x] Dashboard, run detail, Prompt comparison, regression, and 404 pages pass browser smoke tests.
- [x] Mock evaluator works without credentials.
- [ ] OpenAI and DeepSeek provider calls are tested with the maintainer's own credentials.

## Release

- [ ] Move `0.1.0-alpha` changelog entry from Unreleased to the release date.
- [ ] Create tag `v0.1.0-alpha` from `main`.
- [ ] Create a GitHub pre-release using the changelog notes.
- [ ] Verify installation instructions from the public repository.
- [ ] Share only anonymized screenshots and example data.
