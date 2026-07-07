# Contributing

This is a reference architecture repository, maintained the way a
production platform team would maintain an internal service. The process
below is deliberately the same regardless of whether one person or ten are
contributing at a given time.

## Before you start

- For a small, self-contained fix (a bug, a doc correction, a test gap):
  just open a PR.
- For anything that changes an architectural decision (a new AWS service,
  a data model change, a new security boundary, a different deployment
  topology): open an issue first, or at least flag it in the PR description
  as needing an [ADR](docs/adr/README.md). See
  [ADR-0001](docs/adr/0001-record-architecture-decisions.md) for what
  counts as "architecturally significant" and the format to use.

## Development workflow

1. Follow the [development environment guide](docs/guides/development-environment.md)
   to get `make install` and `make install-hooks` done once.
2. Branch from `main`: `phase/<n>-<short-description>` for phase work,
   `fix/<short-description>` for bug fixes -- see
   [naming conventions](docs/standards/naming-conventions.md#git-conventions).
3. Make your change following the [coding standards](docs/standards/coding-standards.md)
   and, if you're adding a feature, the practical checklists in the
   [developer guide](docs/guides/developer-guide.md).
4. Before pushing:
   ```bash
   make format
   make lint
   make typecheck
   make test-cov
   cfn-lint template.yaml bootstrap/*.yaml   # if you touched template.yaml
   sam validate --lint                         # if you touched template.yaml
   ```
   Pre-commit hooks catch most of this automatically on `git commit`; CI
   (`.github/workflows/ci.yml`) re-runs all of it as the actual gate.
5. Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
   (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`), imperative
   mood, explaining *why* in the body when it isn't obvious from the diff
   alone.
6. Open a PR against `main`. CI must pass before merge. Direct pushes to
   `main` are not the intended workflow even where GitHub's branch
   protection isn't enforced (see the note in
   [deployment-strategy.md](docs/guides/deployment-strategy.md) about this
   repository's plan-level limitations) -- treat that as a policy to
   follow voluntarily, not just a rule GitHub enforces for you.

## Definition of done

A PR is ready to merge when:

- [ ] `ruff`, `black --check`, and `mypy --strict` are clean.
- [ ] Tests exist for new behavior and `pytest --cov` stays at or above the
  85% threshold (`pyproject.toml`'s `[tool.coverage.report]`).
- [ ] `template.yaml` changes pass `cfn-lint` and `sam validate --lint`,
  and you've run `sam build --use-container` locally at least once.
- [ ] Documentation that describes the changed behavior is updated in the
  same PR -- not filed as a follow-up. A diagram, ADR, or guide that's
  wrong is worse than one that doesn't exist yet.
- [ ] If the change is architecturally significant, a new ADR is included
  (numbered sequentially, never renumbering an existing one).

## Reporting issues

Include: what you expected, what happened instead, the `job_id` if the
issue involves a specific job (it's the correlation key across every log
and resource -- see the [runbooks](docs/runbooks/README.md) for where to
find it), and which environment (`dev`/`staging`/`prod`) if relevant.
