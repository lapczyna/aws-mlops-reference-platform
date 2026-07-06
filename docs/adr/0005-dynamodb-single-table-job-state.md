# ADR-0005: DynamoDB Single-Table Design for Job State

## Status

Accepted

## Context

The platform needs a durable, low-latency store for batch job metadata
(status, timestamps, S3 pointers, error messages) that:

- Scales to zero cost when idle and scales up automatically under load.
- Supports the two access patterns this platform actually has: fetch a job
  by `job_id`, and (job creation / update) write a job by `job_id`.
- Doesn't require capacity planning or provisioned throughput management.

There is currently no requirement to query jobs by any attribute other than
`job_id` (e.g. "list all jobs for a user" is out of scope for this phase --
see the [roadmap](../roadmap.md) for a possible future multi-tenant
extension).

## Decision

We will use a single **DynamoDB table** (`Jobs`) with:

- Partition key `job_id` (String, ULID) -- no sort key, since there is
  exactly one item per job.
- **On-demand (pay-per-request) billing mode**, not provisioned capacity.
- **Time-to-live (TTL)** on a `ttl` attribute to automatically expire job
  records after a configurable retention window (default 30 days),
  bounding storage cost without a cleanup job.
- No Global Secondary Indexes in this phase. If a future requirement adds a
  "list jobs by status" or "list jobs by submitter" access pattern, that
  will be added as a new ADR alongside the specific GSI design, rather than
  speculatively adding indexes now that would sit unused and cost nothing
  but complexity.

## Consequences

- **Zero idle cost and zero capacity planning:** on-demand billing means we
  pay only for actual reads/writes, with no minimum provisioned throughput.
- **Simple, predictable access pattern:** every read and write in the
  application is a `GetItem`/`PutItem`/`UpdateItem` on a single key --
  there is no query planning or index maintenance to reason about.
- **TTL keeps the table small automatically**, which keeps both storage
  cost and backup/restore time bounded as job volume grows.
- **Trade-off accepted:** without a GSI, there is no way to answer "show me
  all FAILED jobs from the last hour" without a full table scan. This is
  acceptable for the current scope (job status is retrieved by ID, not
  browsed), and is called out explicitly in the
  [roadmap](../roadmap.md) as a candidate future enhancement
  (`status`-based GSI) if a dashboard/admin view is added later.
