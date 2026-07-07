# ADR-0015: CloudWatch Alarms Strategy -- Aggregate Over Per-Resource

## Status

Accepted

## Context

"Production monitoring" could mean anything from zero alarms to one alarm
per metric per resource (which, for six Lambda functions alone, would be
dozens of near-duplicate alarms). Too few alarms means real problems go
unnoticed; too many means the team that's supposed to act on a page
starts ignoring them (alarm fatigue is a well-documented way
operationally-heavy systems become operationally *worse*, not better).

The platform also has both infrastructure-level failure signals (a Lambda
erroring, an API 5xx) and a genuinely different *business*-level signal
(a job completing in a `FAILED` state without any component itself
erroring -- e.g. a client uploading an empty dataset). These call for
different responses and shouldn't be conflated into one alarm.

## Decision

Six alarms, chosen for being both actionable and non-redundant with each
other, documented in `template.yaml` and cross-referenced from
[runbooks](../runbooks/README.md):

1. **`api-5xx`** -- the API is failing calls it should be able to serve.
2. **`lambda-errors`** -- **one aggregate alarm** across all six functions
   using CloudWatch metric math (`Metrics`/`Expression`), not six
   per-function alarms. Which function is at fault is a *triage* question
   (answered by CloudWatch Logs Insights, per the runbooks), not something
   the alarm itself needs to distinguish to be useful -- "something is
   erroring" is already actionable.
3. **`orchestration-failures`** -- a batch job's Step Functions execution
   itself failed (distinct from #4 below: this fires even if the job
   record update mechanism worked fine but the orchestration didn't).
4. **`jobs-table-throttles`** -- DynamoDB is rejecting requests, which
   should essentially never happen on-demand and signals either a genuine
   traffic spike beyond on-demand's burst handling or a hot-key problem.
5. **`job-failure-rate`** -- the business-level signal: 3+ jobs reaching
   `FAILED` in 5 minutes, sourced from the custom `BatchInferencePlatform`
   namespace (ADR emitted by `RecordJobOutcome`), not an AWS-managed
   namespace.
6. A single **CloudWatch dashboard** per environment
   (`OperationsDashboard`) surfaces all of the above plus latency and
   throughput context, rather than requiring every investigation to start
   from the alarm alone.

All alarms notify one SNS topic per environment
(`batch-inference-<env>-alarms`), with an optional email subscription
(`AlarmNotificationEmail` parameter) so a real paging tool (PagerDuty,
Slack, etc.) can subscribe to the same topic without a template change.

## Consequences

- **Fewer, more meaningful pages.** An on-call engineer gets "something in
  Lambda is erroring" once, not six separate near-simultaneous alarms for
  the same underlying incident.
- **Triage still has full detail available** -- the aggregate alarm's
  description points at the specific log-group-glob query
  (`docs/runbooks/api-5xx-errors.md`, `high-failure-rate.md`) to find
  *which* function, the aggregate alarm itself just isn't where that
  answer lives.
- **The business metric alarm requires no infrastructure to be broken** to
  fire -- a wave of `InvalidInput` failures from a misbehaving client looks
  identical to the infrastructure, which is working exactly as designed
  (rejecting bad input), but is still something a team should know about.
- **Thresholds (1 for most, 3 for the business alarm) are starting
  points**, not tuned against real production traffic (there is none yet)
  -- revisit them once real usage data exists, per the note in the
  [cost guide](../guides/cost-guide.md) and the general principle that
  alarm thresholds are operational data, not architectural decisions cast
  in stone at design time.
