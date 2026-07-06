# ML Model Artifact

This directory holds the training script and packaging assets for the
reference inference model. The platform intentionally uses a simple model --
a `scikit-learn` classifier trained on the Iris dataset -- because the
purpose of this repository is to demonstrate MLOps and platform engineering
practices, not modeling technique.

## Contents

| Path                     | Purpose                                                                 |
| ------------------------- | ------------------------------------------------------------------------ |
| `train.py`                 | Trains a `scikit-learn` `RandomForestClassifier` on the Iris dataset and packages it into `model.tar.gz` alongside `inference.py`. |
| `inference.py`             | SageMaker inference entry point (`model_fn`/`input_fn`/`predict_fn`/`output_fn`) used by the Batch Transform container. Runs inside the SageMaker container, not Lambda -- it has no dependency on `batch_inference_platform`. |
| `build/` (generated)        | `train.py`'s output directory, containing `model.tar.gz`. Gitignored -- never committed. |

There is no separate `requirements.txt` in this directory: local training
dependencies (`scikit-learn`, `pandas`, `joblib`) are declared in the
repository's `pyproject.toml` under the `ml` optional-dependency group,
installed with `pip install -e ".[ml]"`. They are deliberately kept out of
`src/requirements.txt` (the Lambda Layer manifest) -- see that file's
comments.

## Training and packaging

```bash
pip install -e ".[ml]"
python ml/train.py --output-dir ml/build
```

This prints the held-out test accuracy and produces `ml/build/model.tar.gz`
containing `model.joblib` and `code/inference.py`, matching the layout the
SageMaker prebuilt scikit-learn container expects (see
[ADR-0009](../docs/adr/0009-sagemaker-model-artifact-parameterization.md)).
To upload it to a deployed environment's model artifacts bucket, use
[`scripts/package_model.sh`](../scripts/package_model.sh).

## Design decisions

- Why SageMaker Batch Transform over a hand-rolled Lambda/Fargate scorer,
  and why Batch Transform over SageMaker Processing:
  [ADR-0003](../docs/adr/0003-sagemaker-batch-transform-vs-processing.md).
- Why the SageMaker Model resource and container image are deploy-time
  parameters rather than requiring this artifact to exist before
  infrastructure can be deployed:
  [ADR-0009](../docs/adr/0009-sagemaker-model-artifact-parameterization.md).
- `train.py` fits on plain numpy arrays rather than a labeled DataFrame --
  see the docstring on `train_model()` for why: scikit-learn's strict
  feature-name matching at predict time would otherwise reject the
  headerless CSV input this platform's inference contract requires.
