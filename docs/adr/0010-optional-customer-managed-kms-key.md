# ADR-0010: Customer-Managed KMS Key as an Opt-In Parameter

## Status

Accepted

## Context

Every AWS storage service used here (S3, DynamoDB) encrypts data at rest by
default using AWS-owned keys, with no configuration required and no
additional cost. Switching to a customer-managed KMS (CMK) key adds real
value in specific situations -- independent audit control over the key
policy, the ability to revoke access by disabling the key, per-environment
key separation -- but also adds real cost (a per-key monthly charge plus
per-request charges for KMS `Encrypt`/`Decrypt`/`GenerateDataKey` calls) and
operational surface (key policy maintenance, rotation, the risk of locking
yourself out of your own data with an over-restrictive policy).

For a `dev` environment used for iteration and demos, that cost and
complexity is very likely not worth it. For a hypothetical regulated `prod`
deployment, it might be exactly what a security team requires. The platform
should support both without forking the template.

## Decision

We add an `EnableCustomerManagedKey` parameter (`true`/`false`, default
`false`). When `true`, a `Condition` (`UseCustomerManagedKey`) causes the
template to create a customer-managed KMS key and alias, and switches every
S3 bucket's default encryption and the DynamoDB table's `SSESpecification`
to use it via `Fn::If`. When `false` (the default), those same resources
use `AES256`/AWS-owned-key encryption with no key management overhead.

## Consequences

- **Encryption at rest is always on**, regardless of this parameter --
  the choice is only about *which key* protects the data, never *whether*
  it's encrypted.
- **`dev` stays free of KMS cost and key-policy maintenance by default**,
  while `staging`/`prod` can opt in via a single parameter override in
  `samconfig.toml`, with no template fork.
- **The key policy grants the account root full control plus scoped
  `Decrypt`/`GenerateDataKey` to the S3 and DynamoDB service principals** --
  narrow enough to avoid an accidental lockout, broad enough that every
  resource in this stack that needs the key can actually use it.
- Toggling this parameter on an existing stack changes the encryption
  configuration of already-provisioned resources in place (S3 re-encrypts
  new writes under the new key; existing objects keep their original
  encryption until rewritten) -- this is standard S3/DynamoDB behavior, not
  specific to this template, but worth knowing before flipping the
  parameter on a stack with existing data.
