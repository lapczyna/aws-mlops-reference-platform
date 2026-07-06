"""SageMaker inference entry point for the Iris classifier.

Implements the `model_fn` / `input_fn` / `predict_fn` / `output_fn` contract
expected by the SageMaker prebuilt scikit-learn inference container. This
file runs inside the SageMaker Batch Transform container, not inside
Lambda -- it has no dependency on the `batch_inference_platform` package
and is packaged into `model.tar.gz` under `code/` by `ml/train.py`. See
ADR-0009 and docs/architecture/overview.md.
"""

from __future__ import annotations

import io
import os
from typing import Any

import joblib
import pandas as pd

FEATURE_COLUMNS = ["sepal_length", "sepal_width", "petal_length", "petal_width"]
_CSV_CONTENT_TYPE = "text/csv"


def model_fn(model_dir: str) -> Any:
    """Load the trained model from the extracted model directory."""
    return joblib.load(os.path.join(model_dir, "model.joblib"))


def input_fn(request_body: str, request_content_type: str) -> pd.DataFrame:
    """Parse a batch of headerless CSV rows (see docs/architecture/overview.md#s3-layout)."""
    if request_content_type != _CSV_CONTENT_TYPE:
        raise ValueError(f"Unsupported content type: {request_content_type}")
    return pd.read_csv(io.StringIO(request_body), header=None, names=FEATURE_COLUMNS)


def predict_fn(input_data: pd.DataFrame, model: Any) -> Any:
    """Run inference for a batch of rows.

    Converts to a bare array before calling predict(): the model is fit on
    unnamed arrays (see ml/train.py), so handing it a named DataFrame would
    only produce a spurious "fitted without feature names" warning on every
    invocation.
    """
    return model.predict(input_data.to_numpy())


def output_fn(prediction: Any, accept: str) -> tuple[str, str]:
    """Serialize predictions as newline-delimited CSV, one label per input row."""
    if accept != _CSV_CONTENT_TYPE:
        raise ValueError(f"Unsupported accept type: {accept}")
    return "\n".join(str(label) for label in prediction), accept
