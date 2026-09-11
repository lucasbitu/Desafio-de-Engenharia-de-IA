from __future__ import annotations

import argparse
import json
import math
import platform
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODELING_DIR = PROJECT_ROOT / "modeling"
EXPERIMENTS_DIR = MODELING_DIR / "experiments"
E01_DIR = EXPERIMENTS_DIR / "e01_unigram"
E02_DIR = EXPERIMENTS_DIR / "e02_balanced"
E03_DIR = EXPERIMENTS_DIR / "e03_bigrams"
sys.path.insert(0, str(E01_DIR))

from train import (  # noqa: E402
    EXPECTED_TRAIN_ROWS,
    EXPECTED_TRAIN_SHA256,
    EXPECTED_VALIDATION_ROWS,
    EXPECTED_VALIDATION_SHA256,
    ID_COLUMN,
    LABEL_COLUMN,
    TEXT_COLUMN,
    build_text_pipeline,
    evaluate,
    example_predictions,
    global_top_features,
    read_split,
    sha256_file,
    validate_splits,
    validation_predictions,
)


DEFAULT_TRAIN = PROJECT_ROOT / "data_split" / "outputs" / "train.csv"
DEFAULT_VALIDATION = PROJECT_ROOT / "data_split" / "outputs" / "validation.csv"
DEFAULT_E01_METRICS = E01_DIR / "outputs" / "validation_metrics.json"
DEFAULT_E02_METRICS = E02_DIR / "outputs" / "validation_metrics.json"
DEFAULT_E03_METRICS = E03_DIR / "outputs" / "validation_metrics.json"
DEFAULT_OUTPUT_DIR = Path(__file__).with_name("outputs")
DEFAULT_REPORT = Path(__file__).with_name("report.md")
EXPERIMENT_NAME = "E04_tfidf_unigram_logreg_moderate_weights"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train E04 with moderate class weights using train and validation only."
    )
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--e01-metrics", type=Path, default=DEFAULT_E01_METRICS)
    parser.add_argument("--e02-metrics", type=Path, default=DEFAULT_E02_METRICS)
    parser.add_argument("--e03-metrics", type=Path, default=DEFAULT_E03_METRICS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def moderate_class_weights(labels: pd.Series) -> dict[str, float]:
    counts = labels.value_counts().sort_index()
    sample_count = int(counts.sum())
    class_count = len(counts)
    raw = {
        str(label): math.sqrt(sample_count / (class_count * int(count)))
        for label, count in counts.items()
    }
    weighted_sum = sum(int(counts[label]) * raw[str(label)] for label in counts.index)
    normalization = sample_count / weighted_sum
    weights = {label: value * normalization for label, value in raw.items()}
    weighted_mean = sum(int(counts[label]) * weights[str(label)] for label in counts.index) / sample_count
    if not math.isclose(weighted_mean, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"Class weights do not have unit sample-weight mean: {weighted_mean}")
    return weights


def prepare_destination(output_dir: Path, report: Path, force: bool) -> None:
    generated = [
        output_dir / name
        for name in (
            "model.joblib",
            "validation_metrics.json",
            "validation_predictions.csv",
            "top_features_by_class.csv",
            "example_predictions.json",
            "run_metadata.json",
        )
    ] + [report]
    existing = [path for path in generated if path.exists()]
    if existing and not force:
        raise FileExistsError("E04 outputs already exist. Use --force to replace them.")
    output_dir.mkdir(parents=True, exist_ok=True)
    if force:
        for path in existing:
            path.unlink()


def read_metrics(path: Path, key: str) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        raise FileNotFoundError(f"Metrics not found: {path}")
    content = json.loads(path.read_text(encoding="utf-8"))
    if key not in content:
        raise ValueError(f"Metrics file does not contain {key}: {path}")
    return content[key], sha256_file(path)


def error_summary(predictions: pd.DataFrame) -> dict[str, int]:
    errors = predictions.loc[~predictions["is_correct"]]
    return {
        "total_errors": int(len(errors)),
        "hardware_false_positives": int(
            ((errors["predicted_class"] == "Hardware") & (errors[LABEL_COLUMN] != "Hardware")).sum()
        ),
        "administrative_rights_false_positives": int(
            (
                (errors["predicted_class"] == "Administrative rights")
                & (errors[LABEL_COLUMN] != "Administrative rights")
            ).sum()
        ),
        "high_confidence_errors": int((errors["confidence"] >= 0.90).sum()),
    }


def metric_delta(new: float, old: float) -> str:
    return f"{new - old:+.4f}"


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *["| " + " | ".join(row) + " |" for row in rows],
        ]
    )


def build_report(
    metrics: dict[str, dict[str, Any]],
    errors: dict[str, int],
    weights: dict[str, float],
    vocabulary_size: int,
    checks: dict[str, bool],
) -> str:
    summary_rows = [
        [name, f"{values['accuracy']:.4f}", f"{values['macro_f1']:.4f}"]
        for name, values in metrics.items()
    ]
    e01 = metrics["E01"]
    e04 = metrics["E04"]
    summary_rows.append(
        [
            "Delta E04 - E01",
            metric_delta(e04["accuracy"], e01["accuracy"]),
            metric_delta(e04["macro_f1"], e01["macro_f1"]),
        ]
    )
    classes = sorted(
        set(e04["classification_report"]) - {"accuracy", "macro avg", "weighted avg"}
    )
    class_rows = []
    for name in classes:
        old = e01["classification_report"][name]
        new = e04["classification_report"][name]
        class_rows.append(
            [
                name,
                f"{old['precision']:.4f}",
                f"{new['precision']:.4f}",
                f"{old['recall']:.4f}",
                f"{new['recall']:.4f}",
                f"{old['f1-score']:.4f}",
                f"{new['f1-score']:.4f}",
                metric_delta(new["f1-score"], old["f1-score"]),
            ]
        )
    weight_rows = [[name, f"{weight:.6f}"] for name, weight in sorted(weights.items())]
    check_rows = [[name, "PASS" if passed else "FAIL"] for name, passed in checks.items()]
    return f"""# E04 - TF-IDF com pesos moderados

## Escopo

O E04 usa os mesmos conjuntos e a mesma configuração do E01. A única mudança é a aplicação de pesos por classe iguais à raiz quadrada dos pesos balanceados, normalizados para peso médio por amostra igual a 1. O teste final não foi acessado.

## Comparação principal

{markdown_table(["Experimento", "Accuracy", "Macro-F1"], summary_rows)}

## E01 versus E04 por classe

{markdown_table(["Classe", "P E01", "P E04", "R E01", "R E04", "F1 E01", "F1 E04", "Delta F1"], class_rows)}

## Pesos aplicados

{markdown_table(["Classe", "Peso"], weight_rows)}

## Erros e complexidade

- Total de erros: **{errors['total_errors']:,}**
- Falsos positivos em `Hardware`: **{errors['hardware_false_positives']:,}**
- Falsos positivos em `Administrative rights`: **{errors['administrative_rights_false_positives']:,}**
- Erros com confiança a partir de 0,90: **{errors['high_confidence_errors']:,}**
- Vocabulário: **{vocabulary_size:,} features**

## Controles

{markdown_table(["Controle", "Resultado"], check_rows)}
"""


def main() -> None:
    args = parse_args()
    prepare_destination(args.output_dir, args.report, args.force)
    train, train_hash = read_split(
        args.train, EXPECTED_TRAIN_ROWS, EXPECTED_TRAIN_SHA256, "train"
    )
    validation, validation_hash = read_split(
        args.validation, EXPECTED_VALIDATION_ROWS, EXPECTED_VALIDATION_SHA256, "validation"
    )
    split_checks = validate_splits(train, validation)
    e01, e01_hash = read_metrics(args.e01_metrics, "E01_tfidf_unigram_logreg")
    e02, e02_hash = read_metrics(args.e02_metrics, "E02_tfidf_unigram_logreg_balanced")
    e03, e03_hash = read_metrics(args.e03_metrics, "E03_tfidf_unigram_bigram_logreg")

    weights = moderate_class_weights(train[LABEL_COLUMN])
    pipeline = build_text_pipeline()
    pipeline.set_params(classifier__class_weight=weights)
    pipeline.fit(train[TEXT_COLUMN], train[LABEL_COLUMN])
    prediction_frame, predictions = validation_predictions(validation, pipeline)
    e04 = evaluate(validation[LABEL_COLUMN], predictions)
    errors = error_summary(prediction_frame)

    vectorizer = pipeline.named_steps["tfidf"]
    vocabulary_size = len(vectorizer.get_feature_names_out())
    weighted_mean = sum(
        int((train[LABEL_COLUMN] == label).sum()) * weight for label, weight in weights.items()
    ) / len(train)
    checks = {
        **split_checks,
        "ngram_range_remains_unigram": vectorizer.ngram_range == (1, 1),
        "custom_class_weights_are_applied": pipeline.named_steps["classifier"].class_weight == weights,
        "sample_weight_mean_is_one": math.isclose(weighted_mean, 1.0, abs_tol=1e-12),
        "weights_are_between_e01_and_e02_extremes": min(weights.values()) < 1.0 < max(weights.values()),
        "same_vocabulary_size_as_e01": vocabulary_size == 8_544,
        "validation_predictions_have_expected_rows": len(prediction_frame) == EXPECTED_VALIDATION_ROWS,
        "prediction_correctness_reconciles": (
            prediction_frame["is_correct"]
            == prediction_frame[LABEL_COLUMN].eq(prediction_frame["predicted_class"])
        ).all(),
    }
    checks = {name: bool(value) for name, value in checks.items()}
    if not all(checks.values()):
        raise ValueError(f"E04 controls failed: {checks}")

    joblib.dump(pipeline, args.output_dir / "model.joblib")
    prediction_frame.to_csv(
        args.output_dir / "validation_predictions.csv", index=False, encoding="utf-8"
    )
    global_top_features(pipeline).to_csv(
        args.output_dir / "top_features_by_class.csv", index=False, encoding="utf-8"
    )
    (args.output_dir / "example_predictions.json").write_text(
        json.dumps(example_predictions(validation, pipeline), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "validation_metrics.json").write_text(
        json.dumps({EXPERIMENT_NAME: e04}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    all_metrics = {"E01": e01, "E02": e02, "E03": e03, "E04": e04}
    metadata = {
        "experiment": EXPERIMENT_NAME,
        "changed_parameter_from_e01": {"class_weight": {"e01": None, "e04": weights}},
        "weight_formula": "normalized_sqrt(N / (K * class_count))",
        "weighted_sample_mean": weighted_mean,
        "test_accessed": False,
        "selection_metric": "macro_f1",
        "train": {"path": str(args.train.resolve()), "rows": len(train), "sha256": train_hash},
        "validation": {
            "path": str(args.validation.resolve()),
            "rows": len(validation),
            "sha256": validation_hash,
        },
        "comparison_inputs": {
            "e01_metrics_sha256": e01_hash,
            "e02_metrics_sha256": e02_hash,
            "e03_metrics_sha256": e03_hash,
        },
        "vocabulary_size": vocabulary_size,
        "errors": errors,
        "checks": checks,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
    }
    (args.output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    args.report.write_text(
        build_report(all_metrics, errors, weights, vocabulary_size, checks), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                name: {"accuracy": values["accuracy"], "macro_f1": values["macro_f1"]}
                for name, values in all_metrics.items()
            }
            | {"errors": errors, "weights": weights},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
