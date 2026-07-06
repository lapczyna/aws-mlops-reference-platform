# ADR-0003: SageMaker Batch Transform over SageMaker Processing

## Status

Accepted

## Context

The platform needs to run a pre-trained `scikit-learn` model against an
uploaded dataset and produce per-row predictions, on a managed, ephemeral,
serverless-compatible compute environment. Two SageMaker capabilities can do
this:

- **SageMaker Processing** -- a general-purpose managed job runner. You
  supply a container and a script; it can do arbitrary data
  processing, feature engineering, model evaluation, or inference. It has no
  built-in concept of a "model" -- you're responsible for loading the model
  artifact and writing an inference loop yourself.
- **SageMaker Batch Transform** -- purpose-built for offline/batch
  inference against a registered SageMaker `Model`. It handles input
  splitting, batching, payload marshaling, and output writing for you, and
  integrates with Step Functions via an **optimized (`.sync`) service
  integration** (`arn:aws:states:::sagemaker:createTransformJob.sync`).

## Decision

We will use **SageMaker Batch Transform**, backed by a SageMaker `Model`
resource wrapping the trained Iris classifier in the pre-built
`scikit-learn` inference container.

## Consequences

- **Less code to write and maintain.** Batch Transform handles input
  splitting/batching and output aggregation; we only implement the
  `model_fn` / `predict_fn` inference contract, not a full data-processing
  script.
- **First-class Step Functions integration.** The `.sync` integration means
  Step Functions polls the transform job's status natively -- no Lambda
  polling loop, no wasted invocations, and job duration is not bounded by
  Lambda's 15-minute limit.
- **Purpose fit.** Batch Transform is the AWS-recommended pattern
  specifically for "run inference against a batch of records already sitting
  in S3," which is exactly this platform's use case. Processing is the
  right tool when the job also needs arbitrary pre/post-processing beyond a
  single model's `predict()` call, which this platform does not currently
  need.
- **Trade-off accepted:** Batch Transform is less flexible than Processing
  if a future requirement needs multi-step feature engineering ahead of
  inference in the same job. Should that arise, the recommended evolution
  is a Step Functions state added *before* `RunBatchTransformJob` (e.g. a
  Processing job for feature engineering), not abandoning Batch Transform for
  the inference step itself.
- Model artifacts must be packaged as `model.tar.gz` and registered as a
  SageMaker `Model` resource before a Transform job can reference it -- this
  packaging step lives in `ml/` and is wired into deployment in Phase 2/3.
