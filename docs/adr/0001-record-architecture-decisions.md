# ADR-0001: Record Architecture Decisions

## Status

Accepted

## Context

Architecturally significant decisions -- ones that are expensive to reverse
or that constrain future work -- need to be discoverable by engineers who
join the project later, including reviewers who only ever see the
repository, not the discussions that produced it. Without a record, the
"why" behind a decision is lost the moment the conversation that produced it
ends, and future engineers either repeat the analysis from scratch or,
worse, silently violate a constraint they didn't know existed.

## Decision

We will record architecture decisions as Architecture Decision Records
(ADRs) in `docs/adr/`, using the lightweight format proposed by Michael
Nygard:

- **Status** -- Proposed, Accepted, Deprecated, or Superseded.
- **Context** -- the forces at play, including technical, business, and
  organizational constraints.
- **Decision** -- the change we're making, stated actively ("We will...").
- **Consequences** -- what becomes easier or harder as a result, including
  trade-offs we are consciously accepting.

ADRs are numbered sequentially and never renumbered or edited to hide a
past decision. If circumstances change, a new ADR supersedes the old one and
both stay in the log.

## Consequences

- Every future PR that changes an architecturally significant decision
  (choice of AWS service, data model, security boundary, deployment
  topology) must include a corresponding ADR.
- The ADR log becomes the canonical source of "why," so README and guide
  documents can stay focused on "what" and "how," linking to ADRs for
  rationale instead of duplicating it.
- Reviewers unfamiliar with the project can reconstruct the reasoning behind
  the architecture without needing access to chat history or tribal
  knowledge.
