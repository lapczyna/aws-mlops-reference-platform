# Architecture Overview

This document describes the system architecture of the Batch Inference
Platform: a serverless reference implementation for submitting datasets,
running asynchronous ML batch inference, and retrieving predictions on AWS.

For step-by-step interaction flows, see
[`sequence-diagrams.md`](sequence-diagrams.md). For the reasoning behind
individual decisions, see the [ADR log](../adr/README.md).

## Scope and non-goals

This platform demonstrates **operational and architectural maturity** for
running batch ML inference in production. It intentionally uses a simple,
pre-trained `scikit-learn` model (Iris classification) as the payload. The
following are explicitly out of scope:

- Model training pipelines, experiment tracking, and feature stores.
- Real-time / low-latency inference (this is a batch system by design).
- Multi-tenant isolation beyond IAM-level resource scoping.

## Guiding constraints

| Constraint                        | Implication                                                                 |
| ----------------------------------- | ------------------------------------------------------------------------------ |
| Serverless-first, near-zero idle cost | No EC2, ECS, EKS, or Aurora. Every compute resource scales to zero and bills per invocation/second. |
| Asynchronous by design               | API Gateway has a hard 29-second integration timeout; batch inference can run for minutes. All job submission is fire-and-poll, never synchronous request/response. See [ADR-0008](../adr/0008-asynchronous-job-processing-pattern.md). |
| Least privilege                      | Every Lambda function and state machine task has a dedicated IAM role scoped to the exact resources and actions it needs -- no shared "execution role" for the whole stack. |
| Observability by default             | Structured JSON logs, correlation IDs (`job_id`) propagated across every hop, and CloudWatch alarms on the failure paths that matter operationally. |

## System context (C4 Level 1)

```mermaid
flowchart LR
    client(["API Consumer\n(data scientist or backend service)"])
    platform[["Batch Inference Platform\nserverless batch ML inference on AWS"]]
    cw[("CloudWatch\nlogs, metrics, dashboards, alarms")]

    client -->|"uploads datasets, submits jobs,\npolls status, retrieves results (HTTPS / REST)"| platform
    platform -->|"emits structured logs and metrics"| cw
```

## Container view (C4 Level 2)

```mermaid
flowchart TB
    subgraph Client
        C[API Consumer]
    end

    subgraph Edge["API Layer"]
        APIGW["API Gateway<br/>(REST API, regional)"]
    end

    subgraph Compute["Compute Layer (AWS Lambda)"]
        L1["PresignUpload<br/>Lambda"]
        L2["SubmitJob<br/>Lambda"]
        L3["GetJobStatus<br/>Lambda"]
        L4["GetJobResults<br/>Lambda"]
    end

    subgraph Orchestration["Orchestration Layer"]
        SFN["Step Functions<br/>State Machine"]
        L5["ValidateInput<br/>Lambda (task)"]
        L6["RecordOutcome<br/>Lambda (task)"]
    end

    subgraph ML["ML Execution"]
        SM["SageMaker<br/>Batch Transform Job"]
    end

    subgraph Storage["Storage Layer"]
        S3in["S3: Datasets Bucket<br/>(raw input, versioned)"]
        S3out["S3: Results Bucket<br/>(predictions, versioned)"]
        DDB["DynamoDB: Jobs Table<br/>(on-demand capacity)"]
    end

    subgraph Obs["Observability"]
        CW["CloudWatch<br/>Logs / Metrics / Alarms / Dashboards"]
    end

    C -->|"1 POST /datasets/upload-url"| APIGW --> L1
    L1 -->|presigned PUT URL| C
    C -->|"2 PUT dataset.csv"| S3in
    C -->|"3 POST /jobs"| APIGW --> L2
    L2 -->|PutItem: status=SUBMITTED| DDB
    L2 -->|StartExecution| SFN
    SFN --> L5 -->|validates dataset exists| S3in
    SFN -->|"CreateTransformJob (.sync)"| SM
    SM -->|reads| S3in
    SM -->|writes predictions| S3out
    SFN --> L6 -->|UpdateItem: status=COMPLETED/FAILED| DDB
    C -->|"4 GET /jobs/{id}"| APIGW --> L3 --> DDB
    C -->|"5 GET /jobs/{id}/results"| APIGW --> L4 --> DDB
    L4 -->|presigned GET URL| S3out

    L1 & L2 & L3 & L4 & L5 & L6 & SFN & SM -.->|logs & metrics| CW
```

**Key design point:** the client never receives inference results directly
from API Gateway. `SubmitJob` returns a `job_id` immediately (HTTP 202); the
client polls `GetJobStatus` and, once `COMPLETED`, calls `GetJobResults` to
receive a presigned S3 URL. This keeps every API Gateway integration well
under its timeout regardless of dataset size or model runtime.

## Component view: Job Orchestration

```mermaid
flowchart LR
    start([Start Execution]) --> validate["ValidateInput\n(Lambda)"]
    validate -->|valid| markProcessing["MarkJobProcessing\n(DynamoDB PutItem,\ndirect SDK integration)"]
    validate -->|invalid| failFast["MarkJobFailed:\nInvalidInput\n(Lambda)"]
    markProcessing --> transform["RunBatchTransformJob\n(SageMaker, .sync integration)"]
    transform -->|success| markCompleted["MarkJobCompleted\n(Lambda)"]
    transform -->|SageMaker error| markFailed["MarkJobFailed:\nTransformError\n(Lambda)"]
    markCompleted --> notify["EmitCompletionMetric\n(CloudWatch EMF)"]
    markFailed --> notifyFail["EmitFailureMetric +\nCloudWatch Alarm"]
    failFast --> notifyFail
    notify --> done([End])
    notifyFail --> done
```

## Step Functions state machine (logical states)

```mermaid
stateDiagram-v2
    [*] --> ValidateInput
    ValidateInput --> MarkProcessing: input valid
    ValidateInput --> MarkFailed: input invalid
    MarkProcessing --> RunBatchTransform
    RunBatchTransform --> MarkCompleted: transform job SUCCEEDED
    RunBatchTransform --> MarkFailed: transform job FAILED / timed out
    MarkCompleted --> [*]
    MarkFailed --> [*]

    note right of RunBatchTransform
        Optimized (.sync) integration:
        arn:aws:states:::sagemaker:createTransformJob.sync
        Step Functions polls SageMaker natively --
        no Lambda polling loop, no wasted invocations.
    end note
```

This ASL definition ships as part of the SAM template in **Phase 2**.

## Data model summary

### DynamoDB -- `Jobs` table

Single-table design, on-demand billing (no idle cost, scales automatically).

| Attribute       | Type   | Notes                                                        |
| ---------------- | ------ | ------------------------------------------------------------- |
| `job_id` (PK)     | String | ULID, sortable by creation time, generated at submission.     |
| `status`          | String | `SUBMITTED` \| `PROCESSING` \| `COMPLETED` \| `FAILED`         |
| `input_s3_key`    | String | Key of the uploaded dataset in the datasets bucket.            |
| `output_s3_key`   | String | Key of the prediction output, populated on completion.         |
| `error_message`   | String | Populated only when `status = FAILED`.                         |
| `created_at`      | String | ISO-8601 UTC timestamp.                                        |
| `updated_at`      | String | ISO-8601 UTC timestamp, updated on every state transition.     |
| `ttl`             | Number | Unix epoch; job records expire automatically after 30 days.    |

Rationale for a single table with no GSIs in the initial design is captured in
[ADR-0005](../adr/0005-dynamodb-single-table-job-state.md).

### S3 layout

```
s3://<datasets-bucket>/uploads/{job_id}/input.csv
s3://<results-bucket>/predictions/{job_id}/output.csv.out
```

Both buckets are versioned, encrypted with SSE-S3 (default) or SSE-KMS
(configurable), block all public access, and enforce TLS-only access via
bucket policy. Lifecycle rules expire objects after a configurable retention
window (default 30 days) to bound storage cost.

## API surface (contract, implemented in Phase 3)

| Method | Path                    | Purpose                                                  |
| ------ | ------------------------ | ----------------------------------------------------------- |
| POST   | `/datasets/upload-url`     | Returns a presigned S3 PUT URL for uploading a dataset.       |
| POST   | `/jobs`                    | Submits a batch inference job referencing an uploaded dataset. Returns `202 Accepted` with a `job_id`. |
| GET    | `/jobs/{jobId}`             | Returns current job status and timestamps.                   |
| GET    | `/jobs/{jobId}/results`     | Returns a presigned S3 GET URL once the job is `COMPLETED`.    |

Request/response schemas are enforced with API Gateway request validation
models (JSON Schema) -- rejecting malformed input at the edge, before it
reaches Lambda. See [ADR-0006](../adr/0006-api-gateway-rest-api-choice.md).

## AWS Well-Architected Framework mapping

| Pillar                    | How this platform addresses it                                                                 |
| --------------------------- | -------------------------------------------------------------------------------------------------- |
| Operational Excellence        | IaC via AWS SAM, structured logging, CloudWatch dashboards, runbooks, ADRs capturing decision history. |
| Security                      | Least-privilege per-function IAM roles, S3 Block Public Access, encryption at rest/in transit, no long-lived credentials, input validation at the API edge. |
| Reliability                   | Step Functions retries/catch blocks, DynamoDB on-demand (no capacity planning), S3 durability (11 nines), idempotent job submission via client-supplied or generated `job_id`. |
| Performance Efficiency        | Serverless compute scales automatically with load; SageMaker Batch Transform scales instance count to dataset size without manual tuning. |
| Cost Optimization              | Pay-per-use across every layer; S3 lifecycle rules; DynamoDB TTL; CloudWatch log retention limits; no idle compute. See the [cost guide](../guides/cost-guide.md) (Phase 4). |
| Sustainability                 | Right-sized, ephemeral compute avoids over-provisioned always-on infrastructure. |

### AWS ML Lens considerations

- **Reproducibility:** model artifact is versioned in S3 and referenced by
  URI/ETag, never mutated in place.
- **Separation of concerns:** training (offline, `ml/`) is decoupled from
  serving (SageMaker Batch Transform), matching the ML Lens guidance to treat
  model artifacts as immutable build outputs.
- **Human-in-the-loop readiness:** job status model has room for a future
  `REVIEW_REQUIRED` state without a breaking schema change.

## Related documents

- [Sequence diagrams](sequence-diagrams.md)
- [ADR log](../adr/README.md)
- [Naming conventions](../standards/naming-conventions.md)
- [Deployment strategy](../guides/deployment-strategy.md)
- [Project roadmap](../roadmap.md)
