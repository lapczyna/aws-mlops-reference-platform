# Sequence Diagrams

Detailed interaction flows for every stage of the batch inference lifecycle.
See [`overview.md`](overview.md) for the static architecture these flows
operate on.

## 1. Dataset upload

The client never uploads directly through API Gateway/Lambda (avoiding
payload-size limits and unnecessary compute cost); it uploads straight to S3
using a short-lived presigned URL.

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant APIGW as API Gateway
    participant Presign as PresignUpload Lambda
    participant S3 as S3 (Datasets Bucket)

    Client->>APIGW: POST /datasets/upload-url
    APIGW->>Presign: invoke(event)
    Presign->>Presign: generate job_id (ULID)
    Presign->>S3: generate_presigned_url(PUT, key=uploads/{job_id}/input.csv)
    Presign-->>APIGW: 200 {job_id, upload_url, expires_in}
    APIGW-->>Client: 200 {job_id, upload_url, expires_in}
    Client->>S3: PUT {upload_url} (dataset bytes)
    S3-->>Client: 200 OK
```

## 2. Batch job submission

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant APIGW as API Gateway
    participant Submit as SubmitJob Lambda
    participant DDB as DynamoDB (Jobs Table)
    participant SFN as Step Functions

    Client->>APIGW: POST /jobs {job_id}
    APIGW->>APIGW: validate request body (JSON Schema)
    APIGW->>Submit: invoke(event)
    Submit->>S3: head_object(uploads/{job_id}/input.csv)
    Note over Submit,S3: fail fast with 404 if dataset was never uploaded
    Submit->>DDB: PutItem(job_id, status=SUBMITTED, created_at, ttl)
    Submit->>SFN: StartExecution(name=job_id, input={job_id, input_s3_key})
    SFN-->>Submit: executionArn
    Submit-->>APIGW: 202 Accepted {job_id, status: SUBMITTED}
    APIGW-->>Client: 202 Accepted {job_id, status: SUBMITTED}
```

`job_id` is used as both the DynamoDB partition key and the Step Functions
execution name, giving the whole system a single, greppable correlation ID
end-to-end -- through CloudWatch Logs, X-Ray traces, and the Step Functions
console.

## 3. State machine orchestration (batch inference execution)

```mermaid
sequenceDiagram
    autonumber
    participant SFN as Step Functions
    participant Validate as ValidateInput Lambda
    participant DDB as DynamoDB (Jobs Table)
    participant SM as SageMaker Batch Transform
    participant S3in as S3 (Datasets Bucket)
    participant S3out as S3 (Results Bucket)
    participant Outcome as RecordOutcome Lambda
    participant CW as CloudWatch

    SFN->>Validate: invoke({job_id, input_s3_key})
    Validate->>S3in: head_object(input_s3_key)
    alt dataset missing or malformed
        Validate-->>SFN: {valid: false, reason}
        SFN->>Outcome: invoke({job_id, status: FAILED, error_code: InvalidInput})
        Outcome->>DDB: UpdateItem(status=FAILED, error_message)
        Outcome->>CW: EmitFailureMetric(reason=InvalidInput) [EMF]
    else dataset valid
        Validate-->>SFN: {valid: true}
        SFN->>DDB: UpdateItem(status=PROCESSING) [direct SDK integration]
        SFN->>SM: CreateTransformJob(.sync) {ModelName, input_s3_key, S3out prefix}
        activate SM
        SM->>S3in: read dataset
        SM->>SM: run inference (Iris classifier)
        SM->>S3out: write predictions (input.csv.out)
        SM-->>SFN: TransformJobStatus = Completed
        deactivate SM
        SFN->>Outcome: invoke({job_id, status: COMPLETED})
        Outcome->>DDB: UpdateItem(status=COMPLETED, output_s3_key, updated_at)
        Outcome->>CW: EmitSuccessMetric(duration) [EMF]
    end
```

The `.sync` service integration (`arn:aws:states:::sagemaker:createTransformJob.sync`)
means Step Functions itself waits on the SageMaker job, with no Lambda
polling loop burning invocations while inference runs.

## 4. Job status check

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant APIGW as API Gateway
    participant Status as GetJobStatus Lambda
    participant DDB as DynamoDB (Jobs Table)

    Client->>APIGW: GET /jobs/{job_id}
    APIGW->>Status: invoke(event)
    Status->>DDB: GetItem(job_id)
    alt job not found
        DDB-->>Status: empty
        Status-->>APIGW: 404 Not Found
    else job found
        DDB-->>Status: {status, created_at, updated_at, error_message?}
        Status-->>APIGW: 200 {job_id, status, ...}
    end
    APIGW-->>Client: response
```

Clients are expected to poll with backoff (see the
[deployment strategy guide](../guides/deployment-strategy.md) for recommended
polling intervals) until `status` is `COMPLETED` or `FAILED`.

## 5. Result retrieval

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant APIGW as API Gateway
    participant Results as GetJobResults Lambda
    participant DDB as DynamoDB (Jobs Table)
    participant S3out as S3 (Results Bucket)

    Client->>APIGW: GET /jobs/{job_id}/results
    APIGW->>Results: invoke(event)
    Results->>DDB: GetItem(job_id)
    alt status != COMPLETED
        Results-->>APIGW: 409 Conflict {status}
    else status == COMPLETED
        Results->>S3out: generate_presigned_url(GET, output_s3_key)
        Results-->>APIGW: 200 {download_url, expires_in}
    end
    APIGW-->>Client: response
```

## 6. Failure handling

```mermaid
sequenceDiagram
    autonumber
    participant SFN as Step Functions
    participant SM as SageMaker Batch Transform
    participant Outcome as RecordOutcome Lambda
    participant DDB as DynamoDB (Jobs Table)
    participant CW as CloudWatch

    SFN->>SM: CreateTransformJob(.sync)
    SM--xSFN: TransformJobStatus = Failed (e.g. malformed record, capacity error)
    Note over SFN: Catch block (States.ALL) routes to RecordFailure with $.error captured
    SFN->>Outcome: invoke({job_id, status: FAILED, error_code, error_cause})
    Outcome->>DDB: UpdateItem(status=FAILED, error_message=cause)
    Outcome->>CW: PutMetricData(JobFailed=1) [EMF] + structured error log
    SFN->>SFN: transition to JobFailed (Fail state)
    CW->>CW: Alarm evaluates failure-rate metric
    Note over CW: Phase 4 wires this alarm to an SNS topic for on-call notification
```

Every failure path writes a terminal `FAILED` state to DynamoDB -- there is no
way for a job to be left in `PROCESSING` indefinitely. Step Functions'
built-in `Retry` (transient errors) and `Catch` (terminal errors) blocks
implement this guarantee; see
[ADR-0004](../adr/0004-step-functions-for-orchestration.md).
