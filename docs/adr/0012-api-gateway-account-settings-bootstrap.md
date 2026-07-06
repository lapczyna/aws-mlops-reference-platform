# ADR-0012: API Gateway Account Settings as a Separate Bootstrap Stack

## Status

Accepted

## Context

API Gateway REST APIs cannot deliver execution logs or access logs to
CloudWatch until the AWS account has a CloudWatch Logs role registered at
the **account level**, via the `AWS::ApiGateway::Account` resource (or the
equivalent console/CLI setting). This setting is not scoped to a single API
or stack -- it is one setting per AWS account per region, full stop.

The obvious place to put that resource would seem to be `template.yaml`
itself, alongside the `JobsApi` resource that needs it. That would be a
mistake: `AWS::Serverless::Api`/`AWS::ApiGateway::Account` is a singleton,
but `template.yaml` is deployed once *per environment* (`dev`, `staging`,
`prod` are three separate stacks, per the
[deployment strategy](../guides/deployment-strategy.md)). If the account
setting lived in each environment's stack, whichever stack deployed last
would silently overwrite the others' configuration of the same
account-wide resource, and deleting any one environment (e.g. tearing down
a `dev` stack, which the deployment strategy explicitly expects to be
routine) would delete or reset a setting that every other environment --
and potentially every other project in the same AWS account -- depends on.

## Decision

The `AWS::ApiGateway::Account` resource and its supporting IAM role live in
a standalone template, `bootstrap/api-gateway-account-settings.yaml`,
deployed **once per AWS account/region**, independently of and prior to any
`template.yaml` environment stack. It is not parameterized by
`Environment` because it does not belong to an environment -- it belongs to
the account.

## Consequences

- **No environment stack's lifecycle can affect another environment's API
  Gateway logging**, because the shared account setting isn't owned by any
  of them.
- **One extra manual step before the first deployment**: an operator (or
  CI, in Phase 4) must deploy the bootstrap stack once. This is documented
  as a prerequisite in the [deployment guide](../guides/deployment-guide.md),
  clearly marked as account-level setup distinct from environment
  deployment.
- **Idempotent to skip.** If the target AWS account already has this
  setting configured (from a previous project or a manual console setup),
  the bootstrap stack can simply be skipped -- `template.yaml` does not
  create or depend on owning this resource, it only depends on the setting
  existing.
- This is the same category of problem as any account-wide singleton
  resource (e.g. a CloudTrail organization trail, an AWS Config recorder);
  the general principle -- singleton account resources get their own
  stack, separate from per-environment application stacks -- applies beyond
  just this one resource if similar needs arise later.
