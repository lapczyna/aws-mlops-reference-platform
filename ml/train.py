"""Trains a RandomForestClassifier on the Iris dataset and packages it for
SageMaker Batch Transform.

Usage:
    python ml/train.py [--output-dir ml/build]

Produces <output-dir>/model.tar.gz containing the serialized model plus the
inference script (see ml/inference.py), ready to upload to the model
artifacts bucket at the key configured by the ModelArtifactS3Key template
parameter (default: model/model.tar.gz). See scripts/package_model.sh,
ADR-0009, and ml/README.md.

Requires the `ml` extra: `pip install -e ".[ml]"`.
"""

from __future__ import annotations

import argparse
import shutil
import tarfile
from pathlib import Path

import joblib
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

_RANDOM_STATE = 42
_THIS_DIR = Path(__file__).resolve().parent


def train_model() -> RandomForestClassifier:
    """Train and evaluate the classifier, printing held-out accuracy.

    Fits on plain numpy arrays rather than a DataFrame: scikit-learn
    records `feature_names_in_` when fit on a DataFrame and then rejects
    predict-time input whose column names don't match exactly. Our
    inference script (ml/inference.py) builds its own DataFrame from
    headerless CSV using FEATURE_COLUMNS, which won't match sklearn's
    default `load_iris` names ("sepal length (cm)", with spaces and
    units) -- fitting on bare arrays avoids that name-matching entirely.
    """
    data = load_iris(as_frame=True)
    x_train, x_test, y_train, y_test = train_test_split(
        data.data.to_numpy(),
        data.target.to_numpy(),
        test_size=0.2,
        random_state=_RANDOM_STATE,
        stratify=data.target,
    )
    model = RandomForestClassifier(n_estimators=100, random_state=_RANDOM_STATE)
    model.fit(x_train, y_train)
    accuracy = model.score(x_test, y_test)
    print(f"Held-out test accuracy: {accuracy:.4f}")
    return model


def package_model(model: RandomForestClassifier, output_dir: Path) -> Path:
    """Serialize the model and bundle it with the inference script into model.tar.gz."""
    staging_dir = output_dir / "_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    code_dir = staging_dir / "code"
    code_dir.mkdir(parents=True)

    joblib.dump(model, staging_dir / "model.joblib")
    shutil.copy(_THIS_DIR / "inference.py", code_dir / "inference.py")

    archive_path = output_dir / "model.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(staging_dir / "model.joblib", arcname="model.joblib")
        tar.add(code_dir / "inference.py", arcname="code/inference.py")

    shutil.rmtree(staging_dir)
    return archive_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=_THIS_DIR / "build")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    model = train_model()
    archive_path = package_model(model, args.output_dir)
    print(f"Packaged model artifact: {archive_path}")


if __name__ == "__main__":
    main()
