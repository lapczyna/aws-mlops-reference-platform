# ADR-0016: Production Approval Gate via GitHub Environments

## Status

Accepted (partially blocked by GitHub plan restrictions -- see below)

## Context

[`deployment-strategy.md`](../guides/deployment-strategy.md) (written in
Phase 1) calls for prod deploys to sit behind a manual approval gate. GitHub
provides exactly one first-class mechanism for this: **Environments** with
a "required reviewers" protection rule -- a workflow job targeting a
protected environment pauses and waits for an approval before it runs.

This repository is private, on GitHub's Free plan. GitHub Environment
protection rules (required reviewers, wait timers, deployment branch
restrictions) require GitHub Team or Enterprise for **private**
repositories -- the same restriction already documented for branch
protection (see the Phase 1 discussion recorded in project memory / prior
session notes) and for [ADR-0012](0012-api-gateway-account-settings-bootstrap.md)'s
kind of account-level singleton concerns, though this one is a GitHub
platform limitation, not an AWS one. Environments themselves (for
scoping secrets/variables) are available on all plans; it's specifically
the *protection rules* that are gated.

## Decision

`deploy-prod.yml`'s `deploy` job targets the `prod` GitHub Environment
regardless of whether the protection rule is currently enforceable. This
means:

- The environment-scoped `AWS_DEPLOY_ROLE_ARN` variable is already wired
  correctly today.
- The moment this repository is made public, or the account upgrades to
  Team/Enterprise, turning on "required reviewers" for the `prod`
  environment is a Settings checkbox -- no workflow change needed.
- Until then, the actual gate is: prod only deploys on an explicit
  `v*.*.*` tag push (never automatically from a merge), which is itself a
  deliberate, human-initiated action, plus the `verify` job re-running the
  full test suite against the exact tagged commit before `deploy` runs.

## Consequences

- **Today, "manual approval" means "a human decides to cut and push a
  tag,"** not "a human clicks approve on a paused deployment." That is a
  real, meaningful gate (it requires deliberate action, and staging must
  have already been validated on the same commit), but it is weaker than a
  second-person review of the specific deployment, which is what the
  protection rule would add.
- **No workaround was implemented** (e.g. a custom manual-approval Action
  using issue comments) specifically to avoid building bespoke
  infrastructure to replace a feature GitHub already provides natively --
  the correct fix is upgrading the plan or repo visibility, not engineering
  around the limitation. This mirrors the decision already made for branch
  protection.
- Anyone deploying this reference architecture for real production use on
  a private repo should budget for GitHub Team (or make the repo public)
  before treating the approval gate as actually enforced, not just
  configured.
