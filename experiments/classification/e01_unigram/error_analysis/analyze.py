"""Analyze E01 validation errors, confidence bands and features."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[4]
MODELING_DIR = PROJECT_ROOT / "experiments" / "classification"
E01_DIR = MODELING_DIR / "e01_unigram"
DEFAULT_PREDICTIONS = E01_DIR / "outputs" / "validation_predictions.csv"
DEFAULT_FEATURES = E01_DIR / "outputs" / "top_features_by_class.csv"
DEFAULT_MODEL = E01_DIR / "outputs" / "baseline_model.joblib"
DEFAULT_OUTPUT_DIR = Path(__file__).with_name("outputs")
DEFAULT_REPORT = Path(__file__).with_name("report.md")

EXPECTED_ROWS = 9_528
EXPECTED_CLASSES = 8
REQUIRED_PREDICTION_COLUMNS = {
    "record_id",
    "source_row",
    "Document",
    "Topic_group",
    "predicted_class",
    "confidence",
    "is_correct",
}
REQUIRED_FEATURE_COLUMNS = {"class", "rank", "feature", "coefficient"}
CONFIDENCE_BINS = [-np.inf, 0.60, 0.75, 0.90, np.inf]
CONFIDENCE_LABELS = ["below_0.60", "0.60_to_0.75", "0.75_to_0.90", "0.90_to_1.00"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit E01 using validation artifacts only.")
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--features", type=Path, default=DEFAULT_FEATURES)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_inputs(
    predictions_path: Path, features_path: Path, model_path: Path
) -> tuple[pd.DataFrame, pd.DataFrame, Pipeline]:
    for path in (predictions_path, features_path, model_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required E01 artifact not found: {path}")

    predictions = pd.read_csv(predictions_path, encoding="utf-8")
    features = pd.read_csv(features_path, encoding="utf-8")
    model = joblib.load(model_path)

    missing_predictions = REQUIRED_PREDICTION_COLUMNS - set(predictions.columns)
    missing_features = REQUIRED_FEATURE_COLUMNS - set(features.columns)
    if missing_predictions:
        raise ValueError(f"Prediction artifact is missing columns: {sorted(missing_predictions)}")
    if missing_features:
        raise ValueError(f"Feature artifact is missing columns: {sorted(missing_features)}")
    if len(predictions) != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS:,} validation rows; found {len(predictions):,}.")
    if predictions["record_id"].isna().any() or not predictions["record_id"].is_unique:
        raise ValueError("Validation predictions contain missing or duplicate record_id values.")
    if predictions["Topic_group"].nunique() != EXPECTED_CLASSES:
        raise ValueError("Validation predictions do not contain all eight actual classes.")
    if predictions["predicted_class"].nunique() != EXPECTED_CLASSES:
        raise ValueError("E01 did not predict all eight classes.")

    predictions["confidence"] = pd.to_numeric(predictions["confidence"], errors="raise")
    predictions["is_correct"] = (
        predictions["is_correct"].astype(str).str.casefold().map({"true": True, "false": False})
    )
    if predictions["is_correct"].isna().any():
        raise ValueError("is_correct contains values other than true or false.")
    recomputed = predictions["Topic_group"] == predictions["predicted_class"]
    if not recomputed.equals(predictions["is_correct"]):
        raise ValueError("Stored is_correct values disagree with actual and predicted labels.")
    if not predictions["confidence"].between(0.0, 1.0).all():
        raise ValueError("Confidence values must be between zero and one.")

    for step in ("tfidf", "classifier"):
        if step not in model.named_steps:
            raise ValueError(f"Saved E01 pipeline is missing step: {step}")
    return predictions, features, model


def error_rate_by_class(predictions: pd.DataFrame) -> pd.DataFrame:
    result = (
        predictions.groupby("Topic_group", observed=True)
        .agg(total=("record_id", "size"), correct=("is_correct", "sum"))
        .reset_index()
        .rename(columns={"Topic_group": "actual_class"})
    )
    result["errors"] = result["total"] - result["correct"]
    result["error_rate"] = result["errors"] / result["total"]
    return result.sort_values(["error_rate", "actual_class"], ascending=[False, True])


def confusion_pairs(predictions: pd.DataFrame) -> pd.DataFrame:
    errors = predictions.loc[~predictions["is_correct"]]
    return (
        errors.groupby(["Topic_group", "predicted_class"], observed=True)
        .agg(
            count=("record_id", "size"),
            mean_confidence=("confidence", "mean"),
            max_confidence=("confidence", "max"),
        )
        .reset_index()
        .rename(columns={"Topic_group": "actual_class"})
        .sort_values(["count", "mean_confidence"], ascending=[False, False])
    )


def confidence_bands(predictions: pd.DataFrame) -> pd.DataFrame:
    working = predictions.copy()
    working["confidence_band"] = pd.cut(
        working["confidence"],
        bins=CONFIDENCE_BINS,
        labels=CONFIDENCE_LABELS,
        right=False,
    )
    result = (
        working.groupby("confidence_band", observed=False)
        .agg(
            total=("record_id", "size"),
            correct=("is_correct", "sum"),
            mean_confidence=("confidence", "mean"),
        )
        .reset_index()
    )
    result["errors"] = result["total"] - result["correct"]
    result["accuracy"] = result["correct"] / result["total"]
    result["error_rate"] = result["errors"] / result["total"]
    return result


def confident_errors(predictions: pd.DataFrame, limit: int = 100) -> pd.DataFrame:
    columns = [
        "record_id",
        "source_row",
        "Document",
        "Topic_group",
        "predicted_class",
        "confidence",
    ]
    return (
        predictions.loc[~predictions["is_correct"], columns]
        .sort_values("confidence", ascending=False)
        .head(limit)
        .rename(columns={"Topic_group": "actual_class"})
    )


def confusion_examples(
    predictions: pd.DataFrame,
    pairs: pd.DataFrame,
    pair_limit: int = 10,
    examples_per_pair: int = 10,
) -> pd.DataFrame:
    errors = predictions.loc[~predictions["is_correct"]]
    selections = []
    for _, pair in pairs.head(pair_limit).iterrows():
        subset = errors.loc[
            (errors["Topic_group"] == pair["actual_class"])
            & (errors["predicted_class"] == pair["predicted_class"])
        ].nlargest(examples_per_pair, "confidence")
        subset = subset.copy()
        subset.insert(0, "pair_total_errors", int(pair["count"]))
        selections.append(subset)
    if not selections:
        return pd.DataFrame()
    return pd.concat(selections, ignore_index=True).rename(
        columns={"Topic_group": "actual_class"}
    )


def feature_audit(
    predictions: pd.DataFrame,
    features: pd.DataFrame,
    model: Pipeline,
    ranks_per_class: int = 15,
) -> pd.DataFrame:
    selected = features.loc[features["rank"] <= ranks_per_class].copy()
    vectorizer = model.named_steps["tfidf"]
    matrix = vectorizer.transform(predictions["Document"])
    vocabulary = vectorizer.vocabulary_
    rows: list[dict[str, Any]] = []

    for row in selected.itertuples(index=False):
        feature_index = vocabulary.get(row.feature)
        if feature_index is None:
            raise ValueError(f"Reported feature not found in saved vocabulary: {row.feature}")
        present = matrix[:, feature_index].getnnz(axis=1) > 0
        predicted_target = predictions["predicted_class"].eq(row._0).to_numpy()
        actual_target = predictions["Topic_group"].eq(row._0).to_numpy()
        feature_and_prediction = present & predicted_target
        true_positive = feature_and_prediction & actual_target
        false_positive = feature_and_prediction & ~actual_target
        prediction_count = int(feature_and_prediction.sum())
        rows.append(
            {
                "class": row._0,
                "rank": int(row.rank),
                "feature": row.feature,
                "coefficient": float(row.coefficient),
                "validation_documents_with_feature": int(present.sum()),
                "predicted_as_class_with_feature": prediction_count,
                "correct_predictions_with_feature": int(true_positive.sum()),
                "false_positives_with_feature": int(false_positive.sum()),
                "precision_when_feature_and_prediction": (
                    float(true_positive.sum() / prediction_count) if prediction_count else None
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["false_positives_with_feature", "coefficient"], ascending=[False, False]
    )


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
        raise FileExistsError("Audit outputs already exist. Use --force to replace them.")
    output_dir.mkdir(parents=True, exist_ok=True)
    if force:
        for path in existing:
            path.unlink()


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    rows = []
    for _, record in frame[columns].iterrows():
        values = []
        for column in columns:
            value = record[column]
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join([header, divider, *rows])


def build_report(
    predictions: pd.DataFrame,
    class_errors: pd.DataFrame,
    pairs: pd.DataFrame,
    bands: pd.DataFrame,
    features: pd.DataFrame,
) -> str:
    total = len(predictions)
    errors = int((~predictions["is_correct"]).sum())
    high_confidence_errors = int(
        ((~predictions["is_correct"]) & (predictions["confidence"] >= 0.90)).sum()
    )
    hardware_absorption = int(
        pairs.loc[pairs["predicted_class"].eq("Hardware"), "count"].sum()
    )
    suspicious = features.loc[
        (features["false_positives_with_feature"] >= 10)
        | (features["precision_when_feature_and_prediction"].fillna(1.0) < 0.70)
    ].head(15)

    return f"""# Auditoria de erros e features do E01

## Escopo

Esta auditoria utiliza somente os artefatos de validação do `E01_tfidf_unigram_logreg`. O teste final não foi acessado.

## Visão geral

- Registros de validação: **{total:,}**
- Erros: **{errors:,}**
- Taxa de erro: **{errors / total:.2%}**
- Erros com confiança a partir de 0,90: **{high_confidence_errors:,}**
- Falsos positivos direcionados a `Hardware`: **{hardware_absorption:,}**

## Taxa de erro por classe real

{markdown_table(class_errors, ["actual_class", "total", "errors", "error_rate"])}

## Principais pares de confusão

{markdown_table(pairs.head(15), ["actual_class", "predicted_class", "count", "mean_confidence", "max_confidence"])}

## Qualidade por faixa de confiança

{markdown_table(bands, ["confidence_band", "total", "errors", "mean_confidence", "accuracy", "error_rate"])}

As faixas descrevem associação entre confiança e acerto, mas não constituem calibração probabilística formal.

## Features prioritárias para revisão humana

O controle abaixo prioriza features entre as 15 maiores de cada classe que aparecem em pelo menos 10 falsos positivos ou cuja precisão, condicionada à presença da feature e à previsão daquela classe, fica abaixo de 70%.

{markdown_table(suspicious, ["class", "feature", "coefficient", "validation_documents_with_feature", "false_positives_with_feature", "precision_when_feature_and_prediction"])}

Uma feature nessa lista não deve ser removida automaticamente. Ela indica onde revisar contexto, vocabulário compartilhado, boilerplate ou possíveis particularidades da taxonomia.

## Hipótese para E02

O E01 apresenta maior taxa de erro em `Administrative rights` e direciona parte relevante dos erros para `Hardware`. O E02 deve alterar somente `class_weight=None` para `class_weight="balanced"` e manter todos os demais parâmetros. A hipótese é que pesos balanceados aumentarão o recall das classes menores e reduzirão a absorção por `Hardware`.

## Critério de decisão

Macro-F1 continuará sendo a métrica principal. Também deverão ser comparados recall e F1 das classes menores, precisão de `Hardware`, quantidade de falsos positivos direcionados a `Hardware` e acurácia geral. O teste final continuará isolado.
"""


def main() -> None:
    args = parse_args()
    prepare_destination(args.output_dir, args.report, args.force)
    predictions, features, model = read_inputs(args.predictions, args.features, args.model)

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

    checks = {
        "validation_has_expected_rows": bool(len(predictions) == EXPECTED_ROWS),
        "record_ids_are_unique": bool(predictions["record_id"].is_unique),
        "all_actual_classes_exist": bool(predictions["Topic_group"].nunique() == EXPECTED_CLASSES),
        "all_predicted_classes_exist": bool(predictions["predicted_class"].nunique() == EXPECTED_CLASSES),
        "stored_correctness_is_consistent": (
            predictions["is_correct"]
            == predictions["Topic_group"].eq(predictions["predicted_class"])
        ).all(),
        "error_counts_reconcile": int(class_errors["errors"].sum())
        == int((~predictions["is_correct"]).sum()),
        "confusion_counts_reconcile": int(pairs["count"].sum())
        == int((~predictions["is_correct"]).sum()),
        "confidence_band_counts_reconcile": int(bands["total"].sum()) == len(predictions),
    }
    checks = {name: bool(value) for name, value in checks.items()}
    if not all(checks.values()):
        raise ValueError(f"Audit reconciliation failed: {checks}")

    metadata = {
        "experiment": "E01_tfidf_unigram_logreg",
        "test_accessed": False,
        "inputs": {
            "predictions": {
                "path": str(args.predictions.resolve()),
                "sha256": sha256_file(args.predictions),
            },
            "features": {
                "path": str(args.features.resolve()),
                "sha256": sha256_file(args.features),
            },
            "model": {
                "path": str(args.model.resolve()),
                "sha256": sha256_file(args.model),
            },
        },
        "parameters": {
            "confident_error_limit": 100,
            "confusion_pair_limit": 10,
            "examples_per_pair": 10,
            "feature_ranks_per_class": 15,
            "confidence_bands": CONFIDENCE_LABELS,
        },
        "checks": checks,
    }
    (args.output_dir / "audit_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    args.report.write_text(
        build_report(predictions, class_errors, pairs, bands, audited_features),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
