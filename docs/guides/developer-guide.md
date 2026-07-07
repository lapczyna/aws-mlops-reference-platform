# Developer Guide

This is the practical "how do I add X" companion to the
[coding standards](../standards/coding-standards.md) (which cover *what the
rules are*) and the [architecture overview](../architecture/overview.md)
(which covers *how the system fits together*). Read those first if you
haven't; this guide assumes them.

## Adding a new REST endpoint

Concretely, the checklist to add e.g. a new `GET /jobs/{jobId}/foo`:

1. **Domain (if needed):** add any new value objects/exceptions to
   `domain/` first. If nothing new needs modeling, skip this.
2. **Application:** add a use case in `application/use_cases/` that takes
   only domain ports as dependencies (never a concrete infrastructure
   class), plus a request/response DTO in `application/dto/` if the shape
   is new.
3. **Infrastructure (if needed):** if the use case needs a capability no
   existing port provides, add the method to the relevant port
   (`domain/ports/`) and implement it on the concrete adapter
   (`infrastructure/`). Don't add infrastructure-specific methods to a port
   "just in case" -- a port only grows when a use case actually needs it.
4. **Handler:** add a new module in `api/handlers/`, following the
   existing handlers' shape: module-level composition root (construct
   clients/adapters/use case once, at cold start), `@logger.inject_lambda_context`
   on the `handler` function, catch domain exceptions and translate them
   to HTTP status codes via `shared/http.json_response`.
5. **Infrastructure as code:** add the function, its dedicated `AWS::Logs::LogGroup`,
   its dedicated `AWS::IAM::Role` (least privilege -- only the actions/resources
   this one handler actually calls, per [ADR-0011](../adr/0011-explicit-per-function-iam-roles.md)),
   and its `Api` event on `JobsApi` in `template.yaml`. If the request has
   a body, add a JSON Schema model under `JobsApi.Properties.Models` and
   reference it via `RequestModel` on the event.
6. **Tests:** a unit test for the use case (against an in-memory fake from
   `tests/unit/fakes.py`, adding a new fake if the port is new) and an
   integration test for the handler (`tests/integration/api/handlers/`,
   following the existing pattern -- set env vars, call `import_handler()`,
   invoke with a `MagicMock()` context).
7. **Docs:** add the route to the API surface table in
   `docs/architecture/overview.md`, and a sequence diagram in
   `docs/architecture/sequence-diagrams.md` if the flow is non-trivial.
8. **Validate:** `make lint && make typecheck && make test-cov`, then
   `cfn-lint template.yaml && sam validate --lint && sam build --use-container`.

## Adding a new Step Functions state

1. Edit `statemachine/job_orchestration.asl.json` directly -- it's checked
   into source control and deployed via `DefinitionUri`, not authored in
   the AWS Console.
2. If the new state needs a new value substituted at deploy time (a new
   Lambda ARN, table name, etc.), add it to both the ASL's `${Placeholder}`
   and `JobOrchestrationStateMachine.Properties.DefinitionSubstitutions`
   in `template.yaml` -- they must match exactly or the deploy fails
   (missing substitution) or silently leaves a literal `${Placeholder}`
   string in the deployed state machine (extra substitution key, silently
   ignored -- no error, so double-check both directions).
3. If the new state calls a new Lambda function, that function's own ARN
   needs `lambda:InvokeFunction` added to `StateMachineExecutionRole`'s
   policy in `template.yaml` -- the *function's own* role doesn't need to
   grant Step Functions anything; the *caller's* (the state machine's) role
   is what needs the invoke permission.
4. Validate the ASL substitution mechanically before deploying (there's no
   `sam local` equivalent for Step Functions): render it with dummy values
   and confirm the result is valid JSON, the same way this repo's own ASL
   was checked in Phase 2 -- substitute every `${...}` token with a
   placeholder string/number and `json.loads()` the result.
5. Update the state diagrams in `docs/architecture/overview.md` and
   `docs/architecture/sequence-diagrams.md` to match -- these are meant to
   be kept in lockstep with the real ASL, not aspirational.

## Debugging

- **CloudWatch Logs Insights** across all Lambda functions at once (useful
  when you only have a `job_id`, not which function to look at first):
  ```
  fields @timestamp, @log, job_id, message
  | filter job_id = "<job_id>"
  | sort @timestamp asc
  ```
  Run against `/aws/lambda/batch-inference-<env>-fn-*` (Logs Insights
  supports a glob across multiple log groups in one query).
- **Local unit tests run in milliseconds** with zero AWS calls
  (`tests/unit/`) -- if you're debugging application logic, reproduce it
  there with a fake before reaching for `sam local invoke` or a real
  deploy.
- **`sam local invoke`** requires Docker and a `--event` JSON file shaped
  like the real trigger (API Gateway proxy event or Step Functions task
  input) -- faster to iterate on than a real deploy, slower than a unit
  test, and still won't catch IAM permission gaps (it runs with your local
  credentials' permissions, not the function's actual role).

## Pitfalls already hit once -- don't repeat them

- **scikit-learn's strict feature-name matching.** If you retrain the
  model and change how it's fit (e.g. back to a labeled DataFrame instead
  of a bare array), `predict()` will start rejecting the headerless CSV
  `ml/inference.py` builds from Batch Transform input. See the docstring
  on `train_model()` in `ml/train.py` for the full explanation.
- **In-memory test fakes need copy semantics.** `FakeJobRepository.get()`
  must return a copy, not the same object reference stored internally --
  otherwise mutating the returned entity in a use case silently mutates
  what the fake considers "already persisted," defeating exactly the kind
  of transition-guard test it's supposed to support. See the comment in
  `tests/unit/fakes.py`.
- **`ruff`'s `S101` (assert) is intentionally *not* ignored for `src/`.**
  If you need a runtime check in application code, `raise` a specific
  exception -- `assert` disappears under Python's `-O` flag and was never
  meant for anything the program's correctness depends on.
