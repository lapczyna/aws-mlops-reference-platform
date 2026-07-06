# ML Model Artifact

This directory holds the training script and packaging assets for the
reference inference model. The platform intentionally uses a simple model --
a `scikit-learn` classifier trained on the Iris dataset -- because the
purpose of this repository is to demonstrate MLOps and platform engineering
practices, not modeling technique.

Model training and packaging are implemented in **Phase 3**, alongside the
batch inference execution path that consumes the resulting artifact.

## Planned contents

| Path                     | Purpose                                                                 |
| ------------------------- | ------------------------------------------------------------------------ |
| `train.py`                 | Trains a `scikit-learn` `RandomForestClassifier` on the Iris dataset and serializes it with `joblib`. |
| `inference.py`             | SageMaker inference entry point (`model_fn`, `predict_fn`) used by the Batch Transform container. |
| `requirements.txt`          | Pinned dependencies for the SageMaker scikit-learn container. |
| `model.tar.gz` (generated)  | Packaged model artifact uploaded to S3 and registered as a SageMaker Model. Never committed to source control. |

## Design decision

Why SageMaker Batch Transform over a hand-rolled Lambda/Fargate scorer, and
why Batch Transform over SageMaker Processing, is documented in
[ADR-0003](../docs/adr/0003-sagemaker-batch-transform-vs-processing.md).
