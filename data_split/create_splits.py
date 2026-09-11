"""Cria splits estratificados, reproduzíveis e auditáveis do dataset de tickets."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

TEXT_COLUMN = "Document"
LABEL_COLUMN = "Topic_group"
EXPECTED_DATASET_SHA256 = "044FDACE33FA564E1E60453F2941DAFC95539C99878B0D32746950394B9DD4D4"
EXPECTED_ROWS = 47_837
TEST_SIZE = 200
VALIDATION_RATIO = 0.20
RANDOM_SEED = 42

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT.parent / "archive" / "all_tickets_processed_improved_v3.csv"
DEFAULT_OUTPUT_DIR = Path(__file__).with_name("outputs")
DEFAULT_REPORT = Path(__file__).with_name("report.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reserva 200 tickets para teste e divide o restante em treino/validação."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--test-size", type=int, default=TEST_SIZE)
    parser.add_argument("--validation-ratio", type=float, default=VALIDATION_RATIO)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Substitui artefatos existentes. Sem esta opção, a sobrescrita é recusada.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_dataset(path: Path) -> tuple[pd.DataFrame, str]:
    if not path.is_file():
        raise FileNotFoundError(f"Dataset não encontrado: {path}")
    errors: list[str] = []
    for encoding in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False), encoding
        except UnicodeDecodeError as error:
            errors.append(f"{encoding}: {error}")
    raise UnicodeError("Não foi possível decodificar o CSV. " + " | ".join(errors))


def validate_source(data: pd.DataFrame, source_hash: str) -> None:
    if source_hash != EXPECTED_DATASET_SHA256:
        raise ValueError(
            "Hash do dataset diferente da versão auditada. "
            f"Esperado: {EXPECTED_DATASET_SHA256}; encontrado: {source_hash}."
        )
    if len(data) != EXPECTED_ROWS:
        raise ValueError(f"Esperados {EXPECTED_ROWS} registros; encontrados {len(data)}.")
    missing = sorted({TEXT_COLUMN, LABEL_COLUMN} - set(data.columns))
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")
    if data[TEXT_COLUMN].isna().any() or data[LABEL_COLUMN].isna().any():
        raise ValueError("O dataset contém texto ou rótulo nulo.")
    if data[TEXT_COLUMN].astype(str).str.strip().eq("").any():
        raise ValueError("O dataset contém texto vazio.")
    if data[LABEL_COLUMN].astype(str).str.strip().eq("").any():
        raise ValueError("O dataset contém rótulo vazio.")


def canonical_record_id(
    dataset_hash: str, source_row: int, document: object, label: object
) -> str:
    payload = {
        "dataset_sha256": dataset_hash,
        "source_row": source_row,
        "document": str(document),
        "topic_group": str(label),
    }
    serialized = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def add_identity(data: pd.DataFrame, dataset_hash: str) -> pd.DataFrame:
    identified = data[[TEXT_COLUMN, LABEL_COLUMN]].copy()
    identified.insert(0, "source_row", range(2, len(identified) + 2))
    identified.insert(
        0,
        "record_id",
        [
            canonical_record_id(dataset_hash, row, document, label)
            for row, document, label in identified[
                ["source_row", TEXT_COLUMN, LABEL_COLUMN]
            ].itertuples(index=False, name=None)
        ],
    )
    if not identified["record_id"].is_unique:
        raise ValueError("A geração de record_id produziu identificadores duplicados.")
    return identified


def proportional_quotas(class_counts: pd.Series, requested_total: int) -> dict[str, int]:
    """Aloca cotas pelo método dos maiores restos, preservando o total exato."""
    if requested_total <= 0 or requested_total >= int(class_counts.sum()):
        raise ValueError("O tamanho solicitado deve estar entre 1 e total-1.")
    exact = class_counts.astype(float) * requested_total / int(class_counts.sum())
    quotas = exact.apply(math.floor).astype(int)
    remaining = requested_total - int(quotas.sum())
    order = sorted(
        class_counts.index,
        key=lambda label: (-(exact[label] - quotas[label]), str(label)),
    )
    for label in order[:remaining]:
        quotas[label] += 1
    return {str(label): int(quotas[label]) for label in class_counts.index}


def stratified_sample(
    data: pd.DataFrame, quotas: dict[str, int], seed: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_parts: list[pd.DataFrame] = []
    for offset, label in enumerate(sorted(quotas)):
        group = data[data[LABEL_COLUMN] == label]
        count = quotas[label]
        if count > len(group):
            raise ValueError(f"Cota {count} excede os {len(group)} registros de {label}.")
        selected_parts.append(group.sample(n=count, random_state=seed + offset))
    selected = pd.concat(selected_parts, ignore_index=False)
    selected = selected.sample(frac=1, random_state=seed).sort_values("source_row")
    remainder = data.drop(index=selected.index).sort_values("source_row")
    return selected.reset_index(drop=True), remainder.reset_index(drop=True)


def build_splits(
    identified: pd.DataFrame, test_size: int, validation_ratio: float, seed: int
) -> dict[str, pd.DataFrame]:
    if not 0 < validation_ratio < 1:
        raise ValueError("validation_ratio deve estar entre 0 e 1.")
    test_quotas = proportional_quotas(
        identified[LABEL_COLUMN].value_counts().sort_index(), test_size
    )
    test, development = stratified_sample(identified, test_quotas, seed)
    validation_size = math.ceil(len(development) * validation_ratio)
    validation_quotas = proportional_quotas(
        development[LABEL_COLUMN].value_counts().sort_index(), validation_size
    )
    validation, train = stratified_sample(development, validation_quotas, seed + 10_000)
    return {"train": train, "validation": validation, "test": test}


def split_manifest(splits: dict[str, pd.DataFrame]) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for split_name, frame in splits.items():
        part = frame[["record_id", "source_row", LABEL_COLUMN]].copy()
        part["split"] = split_name
        parts.append(part)
    return pd.concat(parts, ignore_index=True).sort_values("source_row").reset_index(drop=True)


def validate_splits(
    source: pd.DataFrame, splits: dict[str, pd.DataFrame], test_size: int
) -> dict[str, bool]:
    expected_classes = set(source[LABEL_COLUMN].unique())
    id_sets = {name: set(frame["record_id"]) for name, frame in splits.items()}
    checks = {
        "test_has_exact_requested_size": len(splits["test"]) == test_size,
        "all_rows_are_assigned": sum(map(len, splits.values())) == len(source),
        "all_source_ids_are_preserved": set().union(*id_sets.values()) == set(source["record_id"]),
        "train_validation_do_not_overlap": id_sets["train"].isdisjoint(id_sets["validation"]),
        "train_test_do_not_overlap": id_sets["train"].isdisjoint(id_sets["test"]),
        "validation_test_do_not_overlap": id_sets["validation"].isdisjoint(id_sets["test"]),
        "all_classes_exist_in_train": set(splits["train"][LABEL_COLUMN]) == expected_classes,
        "all_classes_exist_in_validation": set(splits["validation"][LABEL_COLUMN]) == expected_classes,
        "all_classes_exist_in_test": set(splits["test"][LABEL_COLUMN]) == expected_classes,
        "record_ids_remain_unique": all(frame["record_id"].is_unique for frame in splits.values()),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise AssertionError(f"Validações do split falharam: {failed}")
    return checks


def assert_reproducible(
    source: pd.DataFrame,
    first_splits: dict[str, pd.DataFrame],
    test_size: int,
    validation_ratio: float,
    seed: int,
) -> None:
    second_splits = build_splits(source, test_size, validation_ratio, seed)
    first = split_manifest(first_splits)[["record_id", "split"]]
    second = split_manifest(second_splits)[["record_id", "split"]]
    if not first.equals(second):
        raise AssertionError("A repetição com a mesma seed não reproduziu o mesmo split.")


def distribution_table(splits: dict[str, pd.DataFrame]) -> pd.DataFrame:
    counts = {
        name: frame[LABEL_COLUMN].value_counts().sort_index()
        for name, frame in splits.items()
    }
    table = pd.DataFrame(counts).fillna(0).astype(int)
    table["total"] = table.sum(axis=1)
    table.loc["TOTAL"] = table.sum(axis=0)
    return table


def markdown_table(frame: pd.DataFrame) -> str:
    headers = [str(frame.index.name or "Classe"), *map(str, frame.columns)]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] + ["---:"] * len(frame.columns)) + " |",
    ]
    for index, row in frame.iterrows():
        values = [str(index), *[str(value) for value in row.tolist()]]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_report(
    input_path: Path,
    encoding: str,
    dataset_hash: str,
    seed: int,
    validation_ratio: float,
    splits: dict[str, pd.DataFrame],
    checks: dict[str, bool],
    output_hashes: dict[str, str],
) -> str:
    checks_text = "\n".join(
        f"- `{name}`: **{'PASS' if passed else 'FAIL'}**"
        for name, passed in checks.items()
    )
    hashes_text = "\n".join(f"- `{name}`: `{value}`" for name, value in output_hashes.items())
    return f"""# Etapa 4 - Divisão reproduzível dos dados

## Objetivo

Reservar exatamente 200 tickets para a avaliação final e dividir os demais registros em treino e validação sem alterar o dataset original.

## Fonte

- Arquivo: `{input_path.name}`
- Codificação: `{encoding}`
- SHA-256: `{dataset_hash}`
- Registros: **{sum(len(frame) for frame in splits.values()):,}**

## Decisões

- O teste final foi separado antes de treino e validação.
- O teste contém exatamente **{len(splits['test'])} tickets**.
- A seleção é proporcionalmente estratificada por `{LABEL_COLUMN}`.
- A seed é **{seed}**.
- O conjunto de desenvolvimento foi dividido em **{(1 - validation_ratio) * 100:.0f}% treino** e **{validation_ratio * 100:.0f}% validação**.
- As cotas inteiras foram calculadas pelo método dos maiores restos.
- Cada linha recebeu um `record_id` SHA-256 derivado da versão do dataset, linha de origem, texto e rótulo.
- O CSV original não foi modificado e os textos não foram transformados.
- A auditoria de quase duplicatas não foi executada devido ao prazo disponível.

## Distribuição resultante

{markdown_table(distribution_table(splits))}

## Validações

{checks_text}

- `same_seed_reproduces_same_assignment`: **PASS**
- `saved_files_can_be_read_back`: **PASS**

## Arquivos gerados

- `train.csv`: ajuste do TF-IDF e da Logistic Regression.
- `validation.csv`: desenvolvimento e análise de erros.
- `test.csv`: amostra final congelada de 200 tickets.
- `split_manifest.csv`: associação entre registro e partição.
- `split_metadata.json`: parâmetros, contagens, hashes e limitações.

### SHA-256 dos artefatos

{hashes_text}

## Uso correto

O TF-IDF deve executar `fit` somente sobre `train.csv`. Validação e teste devem receber apenas `transform`. Depois de congelar as decisões com a validação, o pipeline poderá ser retreinado em treino mais validação e avaliado uma única vez no teste final.

Os 200 tickets não devem ser substituídos nem regenerados silenciosamente. Uma nova execução sem `--force` recusa sobrescrever os artefatos existentes.

## Limitação aceita

A EDA encontrou zero duplicatas exatas, zero duplicatas após normalização conservadora de espaços e zero conflitos determinísticos. Não foi realizada busca por paráfrases, pequenas alterações lexicais ou cadeias de e-mail parcialmente compartilhadas. Portanto, permanece possível que quase duplicatas atravessem as partições e inflem parcialmente as métricas. Esse risco foi aceito e documentado para concluir a etapa dentro do prazo.
"""


def prepare_destination(output_dir: Path, report_path: Path, force: bool) -> None:
    managed_paths = [
        *(output_dir / name for name in (
            "train.csv", "validation.csv", "test.csv",
            "split_manifest.csv", "split_metadata.json"
        )),
        report_path,
    ]
    existing = [path for path in managed_paths if path.exists()]
    if existing and not force:
        names = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"Artefatos já existem: {names}. Use --force para substituí-los.")


def write_outputs(
    output_dir: Path,
    report_path: Path,
    splits: dict[str, pd.DataFrame],
    metadata_base: dict[str, object],
    input_path: Path,
    encoding: str,
    dataset_hash: str,
    seed: int,
    validation_ratio: float,
    checks: dict[str, bool],
) -> None:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_dir = Path(tempfile.mkdtemp(prefix="split-build-", dir=output_dir.parent))
    try:
        for name, frame in splits.items():
            frame.to_csv(temporary_dir / f"{name}.csv", index=False, encoding="utf-8")
        split_manifest(splits).to_csv(
            temporary_dir / "split_manifest.csv", index=False, encoding="utf-8"
        )
        expected_rows = {
            "train.csv": len(splits["train"]),
            "validation.csv": len(splits["validation"]),
            "test.csv": len(splits["test"]),
            "split_manifest.csv": sum(len(frame) for frame in splits.values()),
        }
        for filename, expected in expected_rows.items():
            reloaded = pd.read_csv(temporary_dir / filename, encoding="utf-8", low_memory=False)
            if len(reloaded) != expected:
                raise AssertionError(
                    f"{filename} deveria ter {expected} linhas; possui {len(reloaded)}."
                )
        output_hashes = {
            filename: sha256_file(temporary_dir / filename) for filename in expected_rows
        }
        metadata = {
            **metadata_base,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "output_sha256": output_hashes,
        }
        (temporary_dir / "split_metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        report = build_report(
            input_path, encoding, dataset_hash, seed, validation_ratio,
            splits, checks, output_hashes
        )
        (temporary_dir / "report.md").write_text(report, encoding="utf-8")
        if output_dir.exists():
            shutil.rmtree(output_dir)
        temporary_dir.replace(output_dir)
        report_path.write_text(report, encoding="utf-8")
    except Exception:
        shutil.rmtree(temporary_dir, ignore_errors=True)
        raise


def main() -> None:
    args = parse_args()
    prepare_destination(args.output_dir, args.report, args.force)
    dataset_hash = sha256_file(args.input)
    data, encoding = read_dataset(args.input)
    validate_source(data, dataset_hash)
    identified = add_identity(data, dataset_hash)
    splits = build_splits(identified, args.test_size, args.validation_ratio, args.seed)
    checks = validate_splits(identified, splits, args.test_size)
    assert_reproducible(identified, splits, args.test_size, args.validation_ratio, args.seed)
    distribution = distribution_table(splits)
    metadata_base: dict[str, object] = {
        "dataset_path": str(args.input.resolve()),
        "dataset_sha256": dataset_hash,
        "dataset_rows": len(identified),
        "text_column": TEXT_COLUMN,
        "label_column": LABEL_COLUMN,
        "random_seed": args.seed,
        "strategy": "proportional_stratified_split_with_explicit_integer_quotas",
        "quota_method": "largest_remainder",
        "test_size": len(splits["test"]),
        "validation_ratio_of_development": args.validation_ratio,
        "train_rows": len(splits["train"]),
        "validation_rows": len(splits["validation"]),
        "test_rows": len(splits["test"]),
        "class_counts_by_split": {
            str(label): {str(column): int(value) for column, value in row.items()}
            for label, row in distribution.drop(index="TOTAL").iterrows()
        },
        "record_id_method": "sha256(canonical_json(dataset_sha256, source_row, document, topic_group))",
        "near_duplicate_audit": "not_performed",
        "near_duplicate_risk": "accepted_and_documented",
        "checks": {**checks, "same_seed_reproduces_same_assignment": True},
    }
    write_outputs(
        args.output_dir, args.report, splits, metadata_base, args.input, encoding,
        dataset_hash, args.seed, args.validation_ratio, checks
    )
    print(distribution.to_string())
    print(f"\nRelatório: {args.report.resolve()}")
    print(f"Artefatos: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()

