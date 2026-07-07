# Design Review

An outside-in review of this repository as it stands at the end of the
planned four-phase roadmap (`v0.4.0`), written the way a staff engineer
would write it for a design review meeting: what's solid, what's a real
gap, and what I'd actually ask to see fixed before this ran real traffic.
The rest of the documentation set (ADRs, guides, threat model) already
makes the case for what was built and why; this document's job is to
argue with it a little.

## Verdict

This is a well-structured reference architecture that does what it claims:
serverless, near-zero idle cost, least-privilege IAM throughout, and a
genuinely tested, genuinely deployable stack rather than a documentation
exercise. The engineering discipline is real -- two dependency CVEs were
found and fixed by actually running `pip-audit`, not just asserting it
would catch things; a real bug in the ML training script was found by
actually running the inference contract, not just writing it. That pattern
-- verify, don't assume -- is the single best thing about how this
repository was built, and it should keep being how anything gets added to
it.

It is not, as-is, ready to hold real user data or real production traffic
without the gaps below being closed first, and the repository is honest
about most of them already (see the [threat model](security/threat-model.md)'s
"known gaps" section and the [roadmap](roadmap.md)'s deferred items). This
review adds a few more, and prioritizes.

## What's genuinely strong

- **Least-privilege IAM is not aspirational here.** Eight hand-written
  roles, each scoped to exactly what its principal does, is more
  discipline than most real production systems have, not less
  ([ADR-0011](adr/0011-explicit-per-function-iam-roles.md)).
- **The ADR log is a real decision record, not decoration.** Sixteen
  ADRs, several of which document *changing your mind* mid-build (the
  `MarkProcessing` `PutItem` → `UpdateItem` correction, the S3 layout
  gaining a third bucket) rather than only recording decisions that
  turned out to be right the first time.
- **Idempotency was designed in, not bolted on** at the DynamoDB and Step
  Functions layer simultaneously ([ADR-0013](adr/0013-idempotent-job-submission.md)),
  which is the kind of thing that's much more expensive to retrofit than
  to build in from the start.
- **No long-lived AWS credentials anywhere**, including in CI
  ([ADR-0014](adr/0014-github-oidc-for-cicd.md)) -- a lot of real
  production systems still fail this bar.

## Findings

### Critical: no caller authentication or authorization

Anyone who can reach the API and knows (or brute-forces) a `job_id` can
read that job's status and download its predictions. `job_id` is a
128-bit-entropy ULID, which makes guessing impractical, but "impractical to
guess" and "authorized" are not the same property, and the difference
matters the moment this stops being a demo. **This is the one finding I
would block a real launch on.** Fix: add an authorizer (API Gateway Lambda
authorizer, Cognito, or IAM auth) and bind `job_id` ownership to a caller
identity in the DynamoDB item. Already tracked in the
[roadmap](roadmap.md); I'd move it to the top.

### High: the design has never been load-tested

`docs/architecture/scalability.md` is careful, reasoned *analysis* --
Lambda concurrency limits, DynamoDB on-demand burst handling, SageMaker's
per-job latency floor. None of it is *measurement*. Every number in that
document is a documented AWS default or a first-principles calculation, not
an observed result from actually sending traffic at this specific
implementation. Before trusting the scalability story, run one: submit a
few hundred concurrent jobs against a `dev` stack and see what actually
breaks first. I'd bet on API Gateway's default stage throttle (currently
20 burst / 10 rate, deliberately conservative) being the first thing to
need tuning, but that's a guess, which is exactly the point.

### High: the deploy role is broader than a security team would sign off on unreviewed

`bootstrap/github-oidc-deploy-role.yaml`'s policy is scoped by
resource-name pattern (`batch-inference-*`) everywhere AWS ARNs support
it, which is genuinely better than the "one big deploy role with
`*:*`" default most teams ship. But within that scoping, most statements
grant the full action wildcard (`s3:*`, `lambda:*`, `dynamodb:*`,
`states:*`, `sagemaker:*`) rather than the specific CRUD actions SAM
deployment actually needs. That's a documented, deliberate trade-off (see
the ADR), and it's a reasonable one for a reference architecture -- but
"reasonable for a demo" and "what I'd approve for a real account with real
customer data behind it" are different bars. A real hardening pass would
enumerate the actual action list `sam deploy` issues (visible via
CloudTrail after a few real deploys) and narrow to that.

### Medium: no dataset content validation beyond "exists and is non-empty"

`ValidateJobInput` confirms the uploaded object exists and has a non-zero
size. It does not confirm the object is actually 4 numeric CSV columns
before handing it to SageMaker -- that check only happens inside
`ml/inference.py`'s `input_fn`, deep inside the Batch Transform container,
where a malformed row surfaces as an opaque container failure rather than
a clear `InvalidInput` rejection at the state-machine validation step
where it belongs. Tightening `ValidateJobInput` to peek at the first row
(without needing to fully parse the dataset) would turn a class of
`TransformError` failures into faster, clearer `InvalidInput` ones -- and
would reduce the SageMaker instance-minutes spent on datasets that were
always going to fail (a cost argument, not just a UX one, per the
[cost guide](guides/cost-guide.md)).

### Medium: the model artifact has no version history or rollback story

`scripts/package_model.sh` overwrites the same S3 key every time. If a
retrain produces a worse model, there is no automatic detection (no
accuracy/drift check gates a new artifact from being used) and no
one-command rollback to the previous artifact -- recovering means
re-running the script from a checkout of the code that produced the old
one. This is exactly the gap the [roadmap](roadmap.md)'s "model
versioning / A-B rollout" item names, but it's worth elevating here: for
an *ML* platform specifically, "which model produced this prediction, and
can I get the previous one back in one command" is a more central concern
than for a typical stateless web service, and it's currently unaddressed.

### Low: alarm thresholds and cost estimates are unvalidated against real usage

Both are explicit about this already (ADR-0015, the cost guide's
disclaimer), so this isn't a new finding so much as a reminder not to let
"it's documented as an estimate" quietly become "it's treated as a fact"
six months from now. Revisit both once real traffic exists.

### Low: this review has an audience of one

Everything in this repository, including this document, was produced in a
single continuous build-out without an independent reviewer at any phase
boundary. The engineering practice throughout is to verify claims by
actually running things rather than asserting them -- which is real and
consistently applied -- but it is not a substitute for a second person's
judgment. Treat every "Accepted" ADR status and every finding in this
review as provisional until someone else has argued with it.

## If I had to pick three things to fix first

1. **Add API authorization.** Everything else in this review is a
   hardening improvement; this one is the difference between "reference
   architecture" and "thing I'd let hold real data."
2. **Run one real load test** against a `dev` stack and correct
   `docs/architecture/scalability.md` and the stage throttle settings
   based on what actually happens, not what's predicted.
3. **Tighten `ValidateJobInput`** to reject malformed dataset content
   before it reaches SageMaker -- cheap to build, and it directly reduces
   both cost (per the cost guide) and mean time to a useful error message.

## Closing note

This concludes the four-phase roadmap this repository was built against.
Per that roadmap's own instructions, work stops here rather than
continuing into a fifth, unplanned phase -- the items above and in
["Beyond Phase 4"](roadmap.md#beyond-phase-4--candidate-future-enhancements)
are the backlog for whoever picks this up next, not a to-do list this
session is going to keep working through.
