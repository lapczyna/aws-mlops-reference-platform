# ADR-0014: GitHub OIDC for CI/CD, No Long-Lived AWS Credentials

## Status

Accepted

## Context

`deploy-staging.yml` and `deploy-prod.yml` need AWS credentials to run
`sam deploy`. The traditional approach -- an IAM user's access key/secret
stored as a GitHub Actions secret -- means a long-lived credential capable
of deploying this platform sits in GitHub indefinitely, is rotatable only
manually, and if ever leaked (a compromised runner, a misconfigured log
that echoes it, a supply-chain-compromised Action) grants the attacker
standing access until someone notices and rotates it.

GitHub Actions supports OIDC: a workflow run can request a short-lived,
cryptographically signed identity token from GitHub, which AWS's STS can
exchange for temporary credentials via `sts:AssumeRoleWithWebIdentity` --
provided the target IAM role's trust policy is configured to accept it.
No credential is stored anywhere; each run mints its own token, valid only
for that run.

## Decision

`bootstrap/github-oidc-deploy-role.yaml` creates (or reuses) the
`token.actions.githubusercontent.com` OIDC provider and one IAM role,
`batch-inference-github-actions-deploy`, whose trust policy matches:

- `token.actions.githubusercontent.com:aud` = `sts.amazonaws.com`
- `token.actions.githubusercontent.com:sub` = `repo:<org>/<repo>:ref:refs/heads/main`
  **or** `repo:<org>/<repo>:ref:refs/tags/v*`

The role's own permissions are scoped by resource-name pattern
(`batch-inference-*`) wherever AWS ARNs support pre-creation scoping (see
the policy comments in the bootstrap template for the documented
exceptions). Both `deploy-staging.yml` and `deploy-prod.yml` use
`aws-actions/configure-aws-credentials` with `role-to-assume` pointing at
this role's ARN (stored as a GitHub Environment variable, not a secret --
it's not sensitive, it's just an ARN).

## Consequences

- **No AWS credential exists in GitHub at all**, not even an encrypted
  secret -- there is nothing to leak from GitHub's side of this
  integration.
- **The trust policy itself is the access control**, scoped tightly enough
  that only a workflow run triggered from this exact repository, on `main`
  or a `v*` tag, can assume the role -- a fork's PR workflow (which
  GitHub explicitly restricts from accessing secrets/OIDC tokens the same
  way regardless) or a different repository cannot.
- **Every deploy rebuilds from source** rather than promoting a
  pre-built artifact between environments, because there is no artifact
  storage step in this design -- `deploy-prod.yml` runs `sam build` fresh
  against the tagged commit. This is a deliberate simplicity trade-off:
  the alternative (build once, promote the same artifact) would need an
  artifact repository and a way to verify staging and prod ran byte-identical
  code, which is more machinery than this reference platform's CD
  needs to prove the concept. A stricter supply-chain posture would
  reconsider this.
- **One-time setup burden**: an operator must deploy the bootstrap stack
  once per AWS account and set the resulting role ARN as an environment
  variable in GitHub -- documented in the
  [deployment guide](../guides/deployment-guide.md).
