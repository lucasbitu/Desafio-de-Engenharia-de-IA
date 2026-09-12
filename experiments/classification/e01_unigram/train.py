"""Historical E01 training experiment: unigram TF-IDF baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import platform
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TRAIN = PROJECT_ROOT / "data" / "splits" / "train.csv"
DEFAULT_VALIDATION = PROJECT_ROOT / "data" / "splits" / "validation.csv"
DEFAULT_OUTPUT_DIR = Path(__file__).with_name("outputs")
DEFAULT_REPORT = Path(__file__).with_name("report.md")
TEXT_COLUMN = "Document"
LABEL_COLUMN = "Topic_group"
ID_COLUMN = "record_id"
REQUIRED_COLUMNS = {ID_COLUMN, "source_row", TEXT_COLUMN, LABEL_COLUMN}
EXPECTED_TRAIN_ROWS = 38_109
EXPECTED_VALIDATION_ROWS = 9_528
EXPECTED_TRAIN_SHA256 = "62DA11CE58FA9EAF6C3AC04A77BE24FC0C66A97864829D68CA98FDBE6FDDF894"
EXPECTED_VALIDATION_SHA256 = "4EEA86B63A3E3D7186C6F52C3FFF41D6D8E266679D7B9496428E3E2971366DB0"
RANDOM_SEED = 42
EXPERIMENT_NAME = "E01_tfidf_unigram_logreg"
LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train E00 and E01 using only frozen train and validation splits."
    )
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
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


def read_split(
    path: Path, expected_rows: int, expected_hash: str, split_name: str
) -> tuple[pd.DataFrame, str]:
    if not path.is_file():
        raise FileNotFoundError(f"{split_name} file not found: {path}")
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        raise ValueError(
            f"Unexpected {split_name} SHA-256. Expected {expected_hash}, found {actual_hash}."
        )
    data = pd.read_csv(path, encoding="utf-8")
    missing = REQUIRED_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"{split_name} is missing columns: {sorted(missing)}")
    if len(data) != expected_rows:
        raise ValueError(f"{split_name} must have {expected_rows:,} rows; found {len(data):,}.")
    if data[ID_COLUMN].isna().any() or data[ID_COLUMN].duplicated().any():
        raise ValueError(f"{split_name} has missing or duplicate record_id values.")
    if data[TEXT_COLUMN].isna().any() or data[TEXT_COLUMN].astype(str).str.strip().eq("").any():
        raise ValueError(f"{split_name} has null or blank texts.")
    if data[LABEL_COLUMN].isna().any() or data[LABEL_COLUMN].astype(str).str.strip().eq("").any():
        raise ValueError(f"{split_name} has null or blank labels.")
    return data, actual_hash


def validate_splits(train: pd.DataFrame, validation: pd.DataFrame) -> dict[str, bool]:
    checks = {
        "train_validation_do_not_overlap": set(train[ID_COLUMN]).isdisjoint(validation[ID_COLUMN]),
        "train_record_ids_are_unique": train[ID_COLUMN].is_unique,
        "validation_record_ids_are_unique": validation[ID_COLUMN].is_unique,
        "class_sets_match": set(train[LABEL_COLUMN]) == set(validation[LABEL_COLUMN]),
        "all_eight_classes_exist": train[LABEL_COLUMN].nunique() == 8,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"Split validation failed: {failed}")
    return checks


def build_text_pipeline() -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    analyzer="word",
                    ngram_range=(1, 1),
                    min_df=2,
                    norm="l2",
                    sublinear_tf=True,
                    dtype=np.float64,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=1.0,
                    solver="lbfgs",
                    max_iter=1_000,
                    class_weight=None,
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )


def evaluate(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, Any]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "classification_report": classification_report(
            y_true, y_pred, output_dict=True, zero_division=0
        ),
    }


def extract_local_evidence(
    pipeline: Pipeline, text: str, predicted_class: str, top_k: int = 4
) -> list[dict[str, Any]]:
    vectorizer: TfidfVectorizer = pipeline.named_steps["tfidf"]
    classifier: LogisticRegression = pipeline.named_steps["classifier"]
    vector = vectorizer.transform([text])
    feature_names = vectorizer.get_feature_names_out()
    class_positions = np.flatnonzero(classifier.classes_ == predicted_class)
    if len(class_positions) != 1:
        raise ValueError(f"Class not found in model: {predicted_class}")
    present_indices = vector.indices
    tfidf_values = vector.data
    weights = classifier.coef_[int(class_positions[0]), present_indices]
    contributions = tfidf_values * weights
    evidence: list[dict[str, Any]] = []
    for position in np.argsort(contributions)[::-1]:
        contribution = float(contributions[position])
        if contribution <= 0:
            continue
        feature_index = int(present_indices[position])
        evidence.append(
            {
                "feature": str(feature_names[feature_index]),
                "tfidf": float(tfidf_values[position]),
                "coefficient": float(weights[position]),
                "contribution": contribution,
            }
        )
        if len(evidence) == top_k:
            break
    return evidence


def deterministic_justification(
    predicted_class: str, evidence: list[dict[str, Any]]
) -> str:
    if not evidence:
        return (
            f"The ticket's overall textual pattern most closely matches {predicted_class}. "
            "The available text contains limited positive term-level evidence."
        )
    terms = [f"'{item['feature']}'" for item in evidence]
    evidence_text = terms[0] if len(terms) == 1 else f"{', '.join(terms[:-1])} and {terms[-1]}"
    return (
        f"The ticket was classified as {predicted_class} because {evidence_text} "
        "provided the strongest positive evidence for this class."
    )


def predict_with_evidence(pipeline: Pipeline, text: str) -> dict[str, Any]:
    classifier: LogisticRegression = pipeline.named_steps["classifier"]
    predicted_class = str(pipeline.predict([text])[0])
    probabilities = pipeline.predict_proba([text])[0]
    class_index = int(np.flatnonzero(classifier.classes_ == predicted_class)[0])
    evidence = extract_local_evidence(pipeline, text, predicted_class)
    return {
        "class": predicted_class,
        "justification": deterministic_justification(predicted_class, evidence),
        "confidence": float(probabilities[class_index]),
        "evidence": evidence,
    }


def global_top_features(pipeline: Pipeline, top_k: int = 30) -> pd.DataFrame:
    vectorizer: TfidfVectorizer = pipeline.named_steps["tfidf"]
    classifier: LogisticRegression = pipeline.named_steps["classifier"]
    names = vectorizer.get_feature_names_out()
    rows = []
    for class_index, class_name in enumerate(classifier.classes_):
        coefficients = classifier.coef_[class_index]
        for rank, feature_index in enumerate(np.argsort(coefficients)[::-1][:top_k], 1):
            rows.append(
                {
                    "class": str(class_name),
                    "rank": rank,
                    "feature": str(names[feature_index]),
                    "coefficient": float(coefficients[feature_index]),
                }
            )
    return pd.DataFrame(rows)


def validation_predictions(
    validation: pd.DataFrame, pipeline: Pipeline
) -> tuple[pd.DataFrame, np.ndarray]:
    predictions = pipeline.predict(validation[TEXT_COLUMN])
    probabilities = pipeline.predict_proba(validation[TEXT_COLUMN])
    output = validation[[ID_COLUMN, "source_row", TEXT_COLUMN, LABEL_COLUMN]].copy()
    output["predicted_class"] = predictions
    output["confidence"] = probabilities.max(axis=1)
    output["is_correct"] = output[LABEL_COLUMN] == output["predicted_class"]
    return output, predictions


def example_predictions(validation: pd.DataFrame, pipeline: Pipeline) -> list[dict[str, Any]]:
    examples = []
    for actual_class in sorted(validation[LABEL_COLUMN].unique()):
        row = validation.loc[validation[LABEL_COLUMN] == actual_class].iloc[0]
        examples.append(
            {
                "record_id": str(row[ID_COLUMN]),
                "actual_class": str(actual_class),
                "text": str(row[TEXT_COLUMN]),
                **predict_with_evidence(pipeline, str(row[TEXT_COLUMN])),
            }
        )
    return examples


def prepare_destination(output_dir: Path, report_path: Path, force: bool) -> None:
    generated = [
        output_dir / name
        for name in (
            "baseline_model.joblib",
            "validation_metrics.json",
            "validation_predictions.csv",
            "top_features_by_class.csv",
            "example_predictions.json",
            "run_metadata.json",
        )
    ] + [report_path]
    existing = [path for path in generated if path.exists()]
    if existing and not force:
        raise FileExistsError("Outputs already exist. Use --force to replace them.")
    output_dir.mkdir(parents=True, exist_ok=True)
    if force:
        for path in existing:
            path.unlink()


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *["| " + " | ".join(row) + " |" for row in rows],
        ]
    )


def build_report(
    metrics: dict[str, Any], vocabulary_size: int, checks: dict[str, bool]
) -> str:
    summary_rows = [
        [name, f"{metrics[name]['accuracy']:.4f}", f"{metrics[name]['macro_f1']:.4f}"]
        for name in ("E00_majority", EXPERIMENT_NAME)
    ]
    report = metrics[EXPERIMENT_NAME]["classification_report"]
    excluded = {"accuracy", "macro avg", "weighted avg"}
    class_rows = [
        [
            name,
            f"{report[name]['precision']:.4f}",
            f"{report[name]['recall']:.4f}",
            f"{report[name]['f1-score']:.4f}",
            str(int(report[name]["support"])),
        ]
        for name in sorted(set(report) - excluded)
    ]
    check_rows = [[name, "PASS" if passed else "FAIL"] for name, passed in checks.items()]
    return f"""# Etapa 5 - Baselines de classificação

## Escopo

Esta execução usou somente treino e validação. O teste final de 200 tickets não foi carregado.

## Experimentos

- `E00_majority`: classe majoritária, sem texto.
- `{EXPERIMENT_NAME}`: TF-IDF de unigramas com Logistic Regression sem pesos.

## Resultados na validação

{markdown_table(["Experimento", "Accuracy", "Macro-F1"], summary_rows)}

## Desempenho por classe do E01

{markdown_table(["Classe", "Precision", "Recall", "F1", "Support"], class_rows)}

## Evidências

- Vocabulário aprendido apenas no treino: **{vocabulary_size:,} features**.
- Evidência local = valor TF-IDF x coeficiente da classe prevista.
- Apenas features presentes no ticket e com contribuição positiva são citadas.
- Nenhum LLM foi utilizado.

## Controles

{markdown_table(["Controle", "Resultado"], check_rows)}

## Próxima decisão

Revisar métricas, features e erros mais confiantes. Depois, comparar separadamente pesos balanceados e bigramas.
"""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args()
    prepare_destination(args.output_dir, args.report, args.force)
    train, train_hash = read_split(
        args.train, EXPECTED_TRAIN_ROWS, EXPECTED_TRAIN_SHA256, "train"
    )
    validation, validation_hash = read_split(
        args.validation, EXPECTED_VALIDATION_ROWS, EXPECTED_VALIDATION_SHA256, "validation"
    )
    checks = validate_splits(train, validation)
    LOGGER.info("Validated %d train and %d validation rows.", len(train), len(validation))

    y_train = train[LABEL_COLUMN]
    y_validation = validation[LABEL_COLUMN]
    majority = DummyClassifier(strategy="most_frequent", random_state=RANDOM_SEED)
    majority.fit(np.zeros((len(train), 1)), y_train)
    majority_pred = majority.predict(np.zeros((len(validation), 1)))

    pipeline = build_text_pipeline()
    LOGGER.info("Training %s.", EXPERIMENT_NAME)
    pipeline.fit(train[TEXT_COLUMN], y_train)
    prediction_frame, model_pred = validation_predictions(validation, pipeline)
    metrics = {
        "E00_majority": evaluate(y_validation, majority_pred),
        EXPERIMENT_NAME: evaluate(y_validation, model_pred),
    }
    for name, result in metrics.items():
        LOGGER.info(
            "%s | accuracy=%.4f | macro_f1=%.4f",
            name,
            result["accuracy"],
            result["macro_f1"],
        )

    vectorizer: TfidfVectorizer = pipeline.named_steps["tfidf"]
    joblib.dump(pipeline, args.output_dir / "baseline_model.joblib")
    prediction_frame.to_csv(
        args.output_dir / "validation_predictions.csv", index=False, encoding="utf-8"
    )
    global_top_features(pipeline).to_csv(
        args.output_dir / "top_features_by_class.csv", index=False, encoding="utf-8"
    )
    (args.output_dir / "validation_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output_dir / "example_predictions.json").write_text(
        json.dumps(example_predictions(validation, pipeline), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    metadata = {
        "experiment": EXPERIMENT_NAME,
        "random_seed": RANDOM_SEED,
        "test_accessed": False,
        "selection_metric": "macro_f1",
        "train": {"path": str(args.train.resolve()), "rows": len(train), "sha256": train_hash},
        "validation": {
            "path": str(args.validation.resolve()),
            "rows": len(validation),
            "sha256": validation_hash,
        },
        "classes": sorted(train[LABEL_COLUMN].unique().tolist()),
        "vocabulary_size": len(vectorizer.get_feature_names_out()),
        "configuration": {
            "tfidf": {
                "ngram_range": [1, 1],
                "min_df": 2,
                "norm": "l2",
                "sublinear_tf": True,
            },
            "logistic_regression": {
                "C": 1.0,
                "solver": "lbfgs",
                "max_iter": 1_000,
                "class_weight": None,
            },
        },
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
        build_report(metrics, metadata["vocabulary_size"], checks), encoding="utf-8"
    )
    LOGGER.info("Artifacts written to %s.", args.output_dir.resolve())


if __name__ == "__main__":
    main()
