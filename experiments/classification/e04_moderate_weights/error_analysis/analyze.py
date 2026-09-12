"""Audit E04 errors, confidence and comparisons before selection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[4]
MODELING_DIR = PROJECT_ROOT / "experiments" / "classification"
EXPERIMENTS_DIR = MODELING_DIR
E01_DIR = EXPERIMENTS_DIR / "e01_unigram"
E02_DIR = EXPERIMENTS_DIR / "e02_balanced"
E04_DIR = EXPERIMENTS_DIR / "e04_moderate_weights"
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


DEFAULT_PREDICTIONS = E04_DIR / "outputs" / "validation_predictions.csv"
DEFAULT_FEATURES = E04_DIR / "outputs" / "top_features_by_class.csv"
DEFAULT_MODEL = E04_DIR / "outputs" / "model.joblib"
DEFAULT_E01_PREDICTIONS = E01_DIR / "outputs" / "validation_predictions.csv"
DEFAULT_E02_PREDICTIONS = E02_DIR / "outputs" / "validation_predictions.csv"
DEFAULT_OUTPUT_DIR = Path(__file__).with_name("outputs")
DEFAULT_REPORT = Path(__file__).with_name("report.md")
EXPERIMENT_NAME = "E04_tfidf_unigram_logreg_moderate_weights"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit E04 using validation artifacts only.")
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--features", type=Path, default=DEFAULT_FEATURES)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--e01-predictions", type=Path, default=DEFAULT_E01_PREDICTIONS)
    parser.add_argument("--e02-predictions", type=Path, default=DEFAULT_E02_PREDICTIONS)
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
        "model_comparison.csv",
        "audit_metadata.json",
    ]
    paths = [output_dir / name for name in names] + [report]
    existing = [path for path in paths if path.exists()]
    if existing and not force:
        raise FileExistsError("E04 audit outputs already exist. Use --force to replace them.")
    output_dir.mkdir(parents=True, exist_ok=True)
    if force:
        for path in existing:
            path.unlink()


def read_comparison_predictions(path: Path, name: str) -> tuple[pd.DataFrame, str]:
    if not path.is_file():
        raise FileNotFoundError(f"{name} predictions not found: {path}")
    frame = pd.read_csv(path, encoding="utf-8")
    if len(frame) != EXPECTED_ROWS or not frame["record_id"].is_unique:
        raise ValueError(f"{name} predictions failed row or identity validation.")
    frame["confidence"] = pd.to_numeric(frame["confidence"], errors="raise")
    frame["is_correct"] = (
        frame["is_correct"].astype(str).str.casefold().map({"true": True, "false": False})
    )
    if frame["is_correct"].isna().any():
        raise ValueError(f"{name} contains invalid is_correct values.")
    return frame, sha256_file(path)


def model_summary(name: str, predictions: pd.DataFrame) -> dict[str, Any]:
    errors = predictions.loc[~predictions["is_correct"]]
    return {
        "model": name,
        "total_errors": int(len(errors)),
        "hardware_false_positives": int(
            ((errors["predicted_class"] == "Hardware") & (errors["Topic_group"] != "Hardware")).sum()
        ),
        "administrative_rights_false_positives": int(
            (
                (errors["predicted_class"] == "Administrative rights")
                & (errors["Topic_group"] != "Administrative rights")
            ).sum()
        ),
        "high_confidence_errors": int((errors["confidence"] >= 0.90).sum()),
    }


def pairwise_changes(reference: pd.DataFrame, candidate: pd.DataFrame) -> dict[str, int]:
    merged = reference[["record_id", "is_correct"]].merge(
        candidate[["record_id", "is_correct"]],
        on="record_id",
        validate="one_to_one",
        suffixes=("_reference", "_candidate"),
    )
    return {
        "both_correct": int((merged["is_correct_reference"] & merged["is_correct_candidate"]).sum()),
        "both_wrong": int((~merged["is_correct_reference"] & ~merged["is_correct_candidate"]).sum()),
        "fixed_by_e04": int((~merged["is_correct_reference"] & merged["is_correct_candidate"]).sum()),
        "broken_by_e04": int((merged["is_correct_reference"] & ~merged["is_correct_candidate"]).sum()),
    }


def feature_review_table(features: pd.DataFrame) -> pd.DataFrame:
    return features.loc[
        (features["false_positives_with_feature"] >= 10)
        | (features["precision_when_feature_and_prediction"].fillna(1.0) < 0.70)
    ].head(15)


def build_report(
    class_errors: pd.DataFrame,
    pairs: pd.DataFrame,
    bands: pd.DataFrame,
    features: pd.DataFrame,
    comparison: pd.DataFrame,
    versus_e01: dict[str, int],
    versus_e02: dict[str, int],
) -> str:
    pair_rows = [
        ["Ambos corretos", str(versus_e01["both_correct"]), str(versus_e02["both_correct"])],
        ["Ambos errados", str(versus_e01["both_wrong"]), str(versus_e02["both_wrong"])],
        ["Corrigidos pelo E04", str(versus_e01["fixed_by_e04"]), str(versus_e02["fixed_by_e04"])],
        ["Introduzidos pelo E04", str(versus_e01["broken_by_e04"]), str(versus_e02["broken_by_e04"])],
    ]
    return f"""# Auditoria de erros e features do E04

## Escopo

Esta auditoria utiliza somente artefatos de validação do `{EXPERIMENT_NAME}` e os compara aos artefatos de validação de E01 e E02. O teste final não foi acessado.

## Comparação operacional

{markdown_table(comparison, ["model", "total_errors", "hardware_false_positives", "administrative_rights_false_positives", "high_confidence_errors"])}

## Comparação registro a registro

{markdown_table(pd.DataFrame(pair_rows, columns=["Resultado", "E04 vs E01", "E04 vs E02"]), ["Resultado", "E04 vs E01", "E04 vs E02"])}

## Taxa de erro por classe real

{markdown_table(class_errors, ["actual_class", "total", "errors", "error_rate"])}

## Principais pares de confusão

{markdown_table(pairs.head(15), ["actual_class", "predicted_class", "count", "mean_confidence", "max_confidence"])}

## Qualidade por faixa de confiança

{markdown_table(bands, ["confidence_band", "total", "errors", "mean_confidence", "accuracy", "error_rate"])}

As faixas medem associação entre confiança e acerto, não calibração formal.

## Features prioritárias para revisão

{markdown_table(feature_review_table(features), ["class", "feature", "coefficient", "validation_documents_with_feature", "false_positives_with_feature", "precision_when_feature_and_prediction"])}

Features são sinais para revisão, não candidatas automáticas à remoção.
"""


def main() -> None:
    args = parse_args()
    prepare_destination(args.output_dir, args.report, args.force)
    e04, features, model = read_inputs(args.predictions, args.features, args.model)
    e01, e01_hash = read_comparison_predictions(args.e01_predictions, "E01")
    e02, e02_hash = read_comparison_predictions(args.e02_predictions, "E02")

    if set(e01["record_id"]) != set(e04["record_id"]) or set(e02["record_id"]) != set(e04["record_id"]):
        raise ValueError("Experiments do not contain the same validation record IDs.")

    class_errors = error_rate_by_class(e04)
    pairs = confusion_pairs(e04)
    bands = confidence_bands(e04)
    confident = confident_errors(e04)
    examples = confusion_examples(e04, pairs)
    audited_features = feature_audit(e04, features, model)
    comparison = pd.DataFrame(
        [model_summary("E01", e01), model_summary("E02", e02), model_summary("E04", e04)]
    )
    versus_e01 = pairwise_changes(e01, e04)
    versus_e02 = pairwise_changes(e02, e04)

    outputs = {
        "error_rate_by_class.csv": class_errors,
        "confusion_pairs.csv": pairs,
        "confidence_bands.csv": bands,
        "confident_errors.csv": confident,
        "confusion_examples.csv": examples,
        "feature_audit.csv": audited_features,
        "model_comparison.csv": comparison,
    }
    for name, frame in outputs.items():
        frame.to_csv(args.output_dir / name, index=False, encoding="utf-8")

    error_total = int((~e04["is_correct"]).sum())
    checks = {
        "validation_has_expected_rows": len(e04) == EXPECTED_ROWS,
        "record_ids_are_unique": e04["record_id"].is_unique,
        "comparison_uses_same_record_ids": set(e01["record_id"]) == set(e02["record_id"]) == set(e04["record_id"]),
        "all_actual_classes_exist": e04["Topic_group"].nunique() == 8,
        "all_predicted_classes_exist": e04["predicted_class"].nunique() == 8,
        "stored_correctness_is_consistent": (
            e04["is_correct"] == e04["Topic_group"].eq(e04["predicted_class"])
        ).all(),
        "error_counts_reconcile": int(class_errors["errors"].sum()) == error_total,
        "confusion_counts_reconcile": int(pairs["count"].sum()) == error_total,
        "confidence_band_counts_reconcile": int(bands["total"].sum()) == len(e04),
        "model_uses_custom_weights": isinstance(model.named_steps["classifier"].class_weight, dict),
    }
    checks = {name: bool(value) for name, value in checks.items()}
    if not all(checks.values()):
        raise ValueError(f"E04 audit checks failed: {checks}")

    metadata = {
        "experiment": EXPERIMENT_NAME,
        "test_accessed": False,
        "pairwise": {"versus_e01": versus_e01, "versus_e02": versus_e02},
        "inputs": {
            "predictions": {"path": str(args.predictions.resolve()), "sha256": sha256_file(args.predictions)},
            "features": {"path": str(args.features.resolve()), "sha256": sha256_file(args.features)},
            "model": {"path": str(args.model.resolve()), "sha256": sha256_file(args.model)},
            "e01_predictions": {"sha256": e01_hash},
            "e02_predictions": {"sha256": e02_hash},
        },
        "checks": checks,
    }
    (args.output_dir / "audit_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    args.report.write_text(
        build_report(
            class_errors,
            pairs,
            bands,
            audited_features,
            comparison,
            versus_e01,
            versus_e02,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
