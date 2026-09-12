"""Historical E02 experiment: fully balanced class weights."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODELING_DIR = PROJECT_ROOT / "experiments" / "classification"
E01_DIR = MODELING_DIR / "e01_unigram"
sys.path.insert(0, str(E01_DIR))

from train import (  # noqa: E402
    EXPECTED_TRAIN_ROWS,
    EXPECTED_TRAIN_SHA256,
    EXPECTED_VALIDATION_ROWS,
    EXPECTED_VALIDATION_SHA256,
    ID_COLUMN,
    LABEL_COLUMN,
    RANDOM_SEED,
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


DEFAULT_TRAIN = PROJECT_ROOT / "data" / "splits" / "train.csv"
DEFAULT_VALIDATION = PROJECT_ROOT / "data" / "splits" / "validation.csv"
DEFAULT_E01_METRICS = E01_DIR / "outputs" / "validation_metrics.json"
DEFAULT_OUTPUT_DIR = Path(__file__).with_name("outputs")
DEFAULT_REPORT = Path(__file__).with_name("report.md")
EXPERIMENT_NAME = "E02_tfidf_unigram_logreg_balanced"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train E02 with balanced class weights using train and validation only."
    )
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--e01-metrics", type=Path, default=DEFAULT_E01_METRICS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


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
        raise FileExistsError("E02 outputs already exist. Use --force to replace them.")
    output_dir.mkdir(parents=True, exist_ok=True)
    if force:
        for path in existing:
            path.unlink()


def read_e01_metrics(path: Path) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        raise FileNotFoundError(f"E01 metrics not found: {path}")
    content = json.loads(path.read_text(encoding="utf-8"))
    key = "E01_tfidf_unigram_logreg"
    if key not in content:
        raise ValueError(f"E01 metrics file does not contain {key}.")
    return content[key], sha256_file(path)


def error_summary(predictions: pd.DataFrame) -> dict[str, Any]:
    errors = predictions.loc[~predictions["is_correct"]]
    hardware_false_positives = int(
        ((errors["predicted_class"] == "Hardware") & (errors[LABEL_COLUMN] != "Hardware")).sum()
    )
    per_class = (
        predictions.groupby(LABEL_COLUMN, observed=True)
        .agg(total=(ID_COLUMN, "size"), correct=("is_correct", "sum"))
        .reset_index()
    )
    per_class["errors"] = per_class["total"] - per_class["correct"]
    per_class["error_rate"] = per_class["errors"] / per_class["total"]
    return {
        "total_errors": int(len(errors)),
        "hardware_false_positives": hardware_false_positives,
        "per_class": per_class.sort_values(LABEL_COLUMN).to_dict(orient="records"),
    }


def metric_delta(e02: float, e01: float) -> str:
    delta = e02 - e01
    return f"{delta:+.4f}"


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *["| " + " | ".join(row) + " |" for row in rows],
        ]
    )


def build_report(
    e01: dict[str, Any],
    e02: dict[str, Any],
    e02_errors: dict[str, Any],
    vocabulary_size: int,
    checks: dict[str, bool],
) -> str:
    summary = [
        ["E01 sem pesos", f"{e01['accuracy']:.4f}", f"{e01['macro_f1']:.4f}"],
        ["E02 balanced", f"{e02['accuracy']:.4f}", f"{e02['macro_f1']:.4f}"],
        [
            "Delta E02 - E01",
            metric_delta(e02["accuracy"], e01["accuracy"]),
            metric_delta(e02["macro_f1"], e01["macro_f1"]),
        ],
    ]
    classes = sorted(
        set(e02["classification_report"])
        - {"accuracy", "macro avg", "weighted avg"}
    )
    class_rows = []
    for class_name in classes:
        old = e01["classification_report"][class_name]
        new = e02["classification_report"][class_name]
        class_rows.append(
            [
                class_name,
                f"{old['precision']:.4f}",
                f"{new['precision']:.4f}",
                metric_delta(new["precision"], old["precision"]),
                f"{old['recall']:.4f}",
                f"{new['recall']:.4f}",
                metric_delta(new["recall"], old["recall"]),
                f"{old['f1-score']:.4f}",
                f"{new['f1-score']:.4f}",
                metric_delta(new["f1-score"], old["f1-score"]),
            ]
        )
    check_rows = [[name, "PASS" if passed else "FAIL"] for name, passed in checks.items()]
    return f"""# E02 - TF-IDF unigramas com pesos balanceados

## Escopo

O E02 reutiliza exatamente os mesmos 38.109 registros de treino e 9.528 de validação do E01. A única mudança de modelagem é `class_weight="balanced"`. O teste final não foi acessado.

## Comparação principal

{markdown_table(["Experimento", "Accuracy", "Macro-F1"], summary)}

## Comparação por classe

{markdown_table(["Classe", "P E01", "P E02", "Delta P", "R E01", "R E02", "Delta R", "F1 E01", "F1 E02", "Delta F1"], class_rows)}

## Erros do E02

- Total de erros: **{e02_errors['total_errors']:,}**
- Falsos positivos direcionados a `Hardware`: **{e02_errors['hardware_false_positives']:,}**
- Vocabulário: **{vocabulary_size:,} features**

## Controles

{markdown_table(["Controle", "Resultado"], check_rows)}

## Regra de interpretação

Macro-F1 é a métrica principal. O efeito esperado é elevar recall e F1 das classes menores e reduzir a absorção por `Hardware`, aceitando apenas uma degradação coerente nas classes maiores. Nenhuma decisão deve usar o teste final.
"""


def main() -> None:
    args = parse_args()
    prepare_destination(args.output_dir, args.report, args.force)
    train, train_hash = read_split(
        args.train, EXPECTED_TRAIN_ROWS, EXPECTED_TRAIN_SHA256, "train"
    )
    validation, validation_hash = read_split(
        args.validation,
        EXPECTED_VALIDATION_ROWS,
        EXPECTED_VALIDATION_SHA256,
        "validation",
    )
    split_checks = validate_splits(train, validation)
    e01_metrics, e01_metrics_hash = read_e01_metrics(args.e01_metrics)

    pipeline = build_text_pipeline()
    pipeline.set_params(classifier__class_weight="balanced")
    pipeline.fit(train[TEXT_COLUMN], train[LABEL_COLUMN])
    prediction_frame, predictions = validation_predictions(validation, pipeline)
    e02_metrics = evaluate(validation[LABEL_COLUMN], predictions)
    e02_errors = error_summary(prediction_frame)

    vectorizer = pipeline.named_steps["tfidf"]
    vocabulary_size = len(vectorizer.get_feature_names_out())
    checks = {
        **split_checks,
        "same_vocabulary_size_as_e01": vocabulary_size == 8_544,
        "class_weight_is_balanced": pipeline.named_steps["classifier"].class_weight == "balanced",
        "validation_predictions_have_expected_rows": len(prediction_frame)
        == EXPECTED_VALIDATION_ROWS,
        "prediction_correctness_reconciles": (
            prediction_frame["is_correct"]
            == prediction_frame[LABEL_COLUMN].eq(prediction_frame["predicted_class"])
        ).all(),
    }
    checks = {name: bool(value) for name, value in checks.items()}
    if not all(checks.values()):
        raise ValueError(f"E02 controls failed: {checks}")

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
        json.dumps({EXPERIMENT_NAME: e02_metrics}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    metadata = {
        "experiment": EXPERIMENT_NAME,
        "changed_parameter_from_e01": {"class_weight": {"e01": None, "e02": "balanced"}},
        "test_accessed": False,
        "selection_metric": "macro_f1",
        "train": {"path": str(args.train.resolve()), "rows": len(train), "sha256": train_hash},
        "validation": {
            "path": str(args.validation.resolve()),
            "rows": len(validation),
            "sha256": validation_hash,
        },
        "e01_metrics": {
            "path": str(args.e01_metrics.resolve()),
            "sha256": e01_metrics_hash,
        },
        "vocabulary_size": vocabulary_size,
        "errors": e02_errors,
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
        build_report(e01_metrics, e02_metrics, e02_errors, vocabulary_size, checks),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "E01": {"accuracy": e01_metrics["accuracy"], "macro_f1": e01_metrics["macro_f1"]},
                "E02": {"accuracy": e02_metrics["accuracy"], "macro_f1": e02_metrics["macro_f1"]},
                "E02_errors": e02_errors["total_errors"],
                "E02_hardware_false_positives": e02_errors["hardware_false_positives"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
