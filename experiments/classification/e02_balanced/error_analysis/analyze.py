"""Compare E02 errors and features against the E01 baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[4]
MODELING_DIR = PROJECT_ROOT / "experiments" / "classification"
E01_DIR = MODELING_DIR / "e01_unigram"
E02_DIR = MODELING_DIR / "e02_balanced"
E01_AUDIT_DIR = E01_DIR / "error_analysis"
sys.path.insert(0, str(E01_AUDIT_DIR))

from analyze import (  # noqa: E402
    EXPECTED_ROWS,
    confidence_bands,
    confident_errors,
    confusion_examples,
    confusion_pairs,
    error_rate_by_class,
    feature_audit,
    markdown_table,
    read_inputs,
    sha256_file,
)


DEFAULT_PREDICTIONS = E02_DIR / "outputs" / "validation_predictions.csv"
DEFAULT_FEATURES = E02_DIR / "outputs" / "top_features_by_class.csv"
DEFAULT_MODEL = E02_DIR / "outputs" / "model.joblib"
DEFAULT_E01_AUDIT = E01_AUDIT_DIR / "outputs" / "audit_metadata.json"
DEFAULT_OUTPUT_DIR = Path(__file__).with_name("outputs")
DEFAULT_REPORT = Path(__file__).with_name("report.md")
EXPERIMENT_NAME = "E02_tfidf_unigram_logreg_balanced"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit E02 using validation artifacts only.")
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--features", type=Path, default=DEFAULT_FEATURES)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--e01-audit", type=Path, default=DEFAULT_E01_AUDIT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def prepare_destination(output_dir: Path, report: Path, force: bool) -> None:
    names = [
        "error_rate_by_class.csv",
        "confusion_pairs.csv",
        "confidence_bands.csv",
        "confident_errors.csv",
        "confusion_examples.csv",
        "feature_audit.csv",
        "audit_metadata.json",
    ]
    paths = [output_dir / name for name in names] + [report]
    existing = [path for path in paths if path.exists()]
    if existing and not force:
        raise FileExistsError("E02 audit outputs already exist. Use --force to replace them.")
    output_dir.mkdir(parents=True, exist_ok=True)
    if force:
        for path in existing:
            path.unlink()


def load_e01_summary(path: Path) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        raise FileNotFoundError(f"E01 audit metadata not found: {path}")
    metadata = json.loads(path.read_text(encoding="utf-8"))
    if metadata.get("experiment") != "E01_tfidf_unigram_logreg":
        raise ValueError("Comparison input is not the expected E01 audit metadata.")

    e01_predictions = E01_DIR / "outputs" / "validation_predictions.csv"
    if not e01_predictions.is_file():
        raise FileNotFoundError(f"E01 validation predictions not found: {e01_predictions}")
    frame = pd.read_csv(e01_predictions, encoding="utf-8")
    frame["is_correct"] = (
        frame["is_correct"].astype(str).str.casefold().map({"true": True, "false": False})
    )
    errors = frame.loc[~frame["is_correct"]]
    return (
        {
            "total_errors": int(len(errors)),
            "hardware_false_positives": int(
                ((errors["predicted_class"] == "Hardware") & (errors["Topic_group"] != "Hardware")).sum()
            ),
            "high_confidence_errors": int((errors["confidence"] >= 0.90).sum()),
        },
        sha256_file(path),
    )


def feature_review_table(features: pd.DataFrame) -> pd.DataFrame:
    return features.loc[
        (features["false_positives_with_feature"] >= 10)
        | (features["precision_when_feature_and_prediction"].fillna(1.0) < 0.70)
    ].head(15)


def build_report(
    predictions: pd.DataFrame,
    class_errors: pd.DataFrame,
    pairs: pd.DataFrame,
    bands: pd.DataFrame,
    features: pd.DataFrame,
    e01: dict[str, int],
) -> str:
    total = len(predictions)
    errors = int((~predictions["is_correct"]).sum())
    high_confidence_errors = int(
        ((~predictions["is_correct"]) & (predictions["confidence"] >= 0.90)).sum()
    )
    hardware_false_positives = int(
        pairs.loc[pairs["predicted_class"].eq("Hardware"), "count"].sum()
    )
    admin_false_positives = int(
        pairs.loc[pairs["predicted_class"].eq("Administrative rights"), "count"].sum()
    )
    admin_from_hardware = int(
        pairs.loc[
            pairs["actual_class"].eq("Hardware")
            & pairs["predicted_class"].eq("Administrative rights"),
            "count",
        ].sum()
    )
    comparison_rows = [
        ["Total de erros", str(e01["total_errors"]), str(errors), f"{errors - e01['total_errors']:+d}"],
        [
            "Falsos positivos em Hardware",
            str(e01["hardware_false_positives"]),
            str(hardware_false_positives),
            f"{hardware_false_positives - e01['hardware_false_positives']:+d}",
        ],
        [
            "Erros com confiança >= 0,90",
            str(e01["high_confidence_errors"]),
            str(high_confidence_errors),
            f"{high_confidence_errors - e01['high_confidence_errors']:+d}",
        ],
    ]
    return f"""# Auditoria de erros e features do E02

## Escopo

Esta auditoria utiliza somente os artefatos de validação do `{EXPERIMENT_NAME}`. O teste final não foi acessado.

## Comparação com E01

{markdown_table(pd.DataFrame(comparison_rows, columns=["Métrica", "E01", "E02", "Delta"]), ["Métrica", "E01", "E02", "Delta"])}

O E02 possui **{admin_false_positives:,}** falsos positivos direcionados a `Administrative rights`; **{admin_from_hardware:,}** vieram de `Hardware`.

## Taxa de erro por classe real

{markdown_table(class_errors, ["actual_class", "total", "errors", "error_rate"])}

## Principais pares de confusão

{markdown_table(pairs.head(15), ["actual_class", "predicted_class", "count", "mean_confidence", "max_confidence"])}

## Qualidade por faixa de confiança

{markdown_table(bands, ["confidence_band", "total", "errors", "mean_confidence", "accuracy", "error_rate"])}

As faixas medem associação entre confiança e acerto, não calibração probabilística formal.

## Features prioritárias para revisão

{markdown_table(feature_review_table(features), ["class", "feature", "coefficient", "validation_documents_with_feature", "false_positives_with_feature", "precision_when_feature_and_prediction"])}

Uma feature listada não deve ser removida automaticamente. O objetivo é identificar vocabulário compartilhado e mudanças causadas pelos pesos.

## Interpretação

O balanceamento reduz a absorção por `Hardware`, mas desloca erros para classes menores, sobretudo `Administrative rights`. A decisão deve considerar a troca entre recall e precisão, a quantidade de erros confiantes e a coerência semântica dos novos falsos positivos.
"""


def main() -> None:
    args = parse_args()
    prepare_destination(args.output_dir, args.report, args.force)
    predictions, features, model = read_inputs(args.predictions, args.features, args.model)
    e01_summary, e01_audit_hash = load_e01_summary(args.e01_audit)

    class_errors = error_rate_by_class(predictions)
    pairs = confusion_pairs(predictions)
    bands = confidence_bands(predictions)
    confident = confident_errors(predictions)
    examples = confusion_examples(predictions, pairs)
    audited_features = feature_audit(predictions, features, model)

    outputs = {
        "error_rate_by_class.csv": class_errors,
        "confusion_pairs.csv": pairs,
        "confidence_bands.csv": bands,
        "confident_errors.csv": confident,
        "confusion_examples.csv": examples,
        "feature_audit.csv": audited_features,
    }
    for name, frame in outputs.items():
        frame.to_csv(args.output_dir / name, index=False, encoding="utf-8")

    error_total = int((~predictions["is_correct"]).sum())
    checks = {
        "validation_has_expected_rows": len(predictions) == EXPECTED_ROWS,
        "record_ids_are_unique": predictions["record_id"].is_unique,
        "all_actual_classes_exist": predictions["Topic_group"].nunique() == 8,
        "all_predicted_classes_exist": predictions["predicted_class"].nunique() == 8,
        "stored_correctness_is_consistent": (
            predictions["is_correct"]
            == predictions["Topic_group"].eq(predictions["predicted_class"])
        ).all(),
        "error_counts_reconcile": int(class_errors["errors"].sum()) == error_total,
        "confusion_counts_reconcile": int(pairs["count"].sum()) == error_total,
        "confidence_band_counts_reconcile": int(bands["total"].sum()) == len(predictions),
        "model_uses_balanced_weights": model.named_steps["classifier"].class_weight == "balanced",
    }
    checks = {name: bool(value) for name, value in checks.items()}
    if not all(checks.values()):
        raise ValueError(f"E02 audit checks failed: {checks}")

    metadata = {
        "experiment": EXPERIMENT_NAME,
        "test_accessed": False,
        "comparison": {"e01": e01_summary},
        "inputs": {
            "predictions": {"path": str(args.predictions.resolve()), "sha256": sha256_file(args.predictions)},
            "features": {"path": str(args.features.resolve()), "sha256": sha256_file(args.features)},
            "model": {"path": str(args.model.resolve()), "sha256": sha256_file(args.model)},
            "e01_audit": {"path": str(args.e01_audit.resolve()), "sha256": e01_audit_hash},
        },
        "parameters": {
            "confident_error_limit": 100,
            "confidence_threshold": 0.90,
            "confusion_pair_limit": 10,
            "examples_per_pair": 10,
            "feature_ranks_per_class": 15,
        },
        "checks": checks,
    }
    (args.output_dir / "audit_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    args.report.write_text(
        build_report(predictions, class_errors, pairs, bands, audited_features, e01_summary),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
