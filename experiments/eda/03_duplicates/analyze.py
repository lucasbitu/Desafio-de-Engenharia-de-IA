"""Etapa 3 da EDA: duplicatas exatas, normalizadas e conflitos de rótulo."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


TEXT_COLUMN = "Document"
LABEL_COLUMN = "Topic_group"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = PROJECT_ROOT.parent / "archive" / "all_tickets_processed_improved_v3.csv"
OUTPUT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audita duplicatas de texto e conflitos de rótulo no dataset."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def read_dataset(path: Path) -> tuple[pd.DataFrame, str]:
    if not path.is_file():
        raise FileNotFoundError(f"Dataset não encontrado: {path}")

    decoding_errors: list[str] = []
    for encoding in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False), encoding
        except UnicodeDecodeError as error:
            decoding_errors.append(f"{encoding}: {error}")

    details = " | ".join(decoding_errors)
    raise UnicodeError(f"Não foi possível decodificar o CSV. Tentativas: {details}")


def validate_schema(data: pd.DataFrame) -> None:
    required = {TEXT_COLUMN, LABEL_COLUMN}
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")
    if data.empty:
        raise ValueError("O dataset não contém registros.")


def normalize_whitespace(value: object) -> str:
    """Remove espaços externos e colapsa espaços internos sem alterar palavras."""
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def duplicate_group_id(text: pd.Series) -> pd.Series:
    """Cria identificador reproduzível sem expor o texto no identificador."""
    return pd.util.hash_pandas_object(text, index=False).astype(str)


def audit_duplicates(data: pd.DataFrame) -> dict[str, object]:
    audit = data[[TEXT_COLUMN, LABEL_COLUMN]].copy()
    audit.insert(0, "source_row", audit.index + 2)
    audit["normalized_text"] = audit[TEXT_COLUMN].map(normalize_whitespace)
    audit["normalized_group_id"] = duplicate_group_id(audit["normalized_text"])

    exact_pair_mask = audit.duplicated(
        subset=[TEXT_COLUMN, LABEL_COLUMN], keep=False
    )
    exact_pair_rows = audit.loc[exact_pair_mask].copy()
    exact_pair_excess = len(audit) - len(
        audit.drop_duplicates(subset=[TEXT_COLUMN, LABEL_COLUMN])
    )

    exact_text_mask = audit[TEXT_COLUMN].notna() & audit.duplicated(
        subset=[TEXT_COLUMN], keep=False
    )
    exact_text_rows = audit.loc[exact_text_mask].copy()
    exact_text_group_count = int(exact_text_rows[TEXT_COLUMN].nunique(dropna=True))

    valid_normalized = audit["normalized_text"].ne("")
    normalized_duplicate_mask = valid_normalized & audit.duplicated(
        subset=["normalized_text"], keep=False
    )
    normalized_duplicate_rows = audit.loc[normalized_duplicate_mask].copy()
    normalized_group_count = int(
        normalized_duplicate_rows["normalized_text"].nunique()
    )

    label_count_by_text = (
        audit.loc[valid_normalized]
        .groupby("normalized_text")[LABEL_COLUMN]
        .nunique(dropna=False)
    )
    conflicting_texts = label_count_by_text[label_count_by_text > 1].index
    conflict_rows = audit[audit["normalized_text"].isin(conflicting_texts)].copy()
    conflict_rows = conflict_rows.sort_values(
        ["normalized_group_id", LABEL_COLUMN, "source_row"]
    )

    same_label_normalized = normalized_duplicate_rows[
        ~normalized_duplicate_rows["normalized_text"].isin(conflicting_texts)
    ].copy()

    export_columns = [
        "normalized_group_id",
        "source_row",
        LABEL_COLUMN,
        TEXT_COLUMN,
        "normalized_text",
    ]
    return {
        "total_rows": len(audit),
        "exact_pair_rows": exact_pair_rows[export_columns],
        "exact_pair_excess": int(exact_pair_excess),
        "exact_text_rows": exact_text_rows[export_columns],
        "exact_text_group_count": exact_text_group_count,
        "normalized_duplicate_rows": normalized_duplicate_rows[export_columns],
        "normalized_group_count": normalized_group_count,
        "same_label_normalized_rows": same_label_normalized[export_columns],
        "conflict_rows": conflict_rows[export_columns],
        "conflicting_group_count": int(len(conflicting_texts)),
    }


def percentage(count: int, total: int) -> str:
    return f"{count / total * 100:.4f}%"


def build_report(results: dict[str, object], source: Path, encoding: str) -> str:
    total = int(results["total_rows"])
    exact_pair_rows = results["exact_pair_rows"]
    exact_text_rows = results["exact_text_rows"]
    normalized_rows = results["normalized_duplicate_rows"]
    same_label_rows = results["same_label_normalized_rows"]
    conflict_rows = results["conflict_rows"]

    return f"""# Etapa 3 - Auditoria de duplicatas

## Objetivo

Identificar repetições determinísticas e conflitos de rótulo antes de qualquer limpeza ou divisão entre treino e avaliação. Esta etapa não remove nem altera registros.

## Fonte e método

- Arquivo analisado: `{source.name}`
- Codificação utilizada: `{encoding}`
- Registros analisados: **{total:,}**
- Linha de origem: número físico aproximado no CSV, considerando o cabeçalho como linha 1
- Normalização de auditoria: remoção de espaços externos e substituição de sequências de espaços por um único espaço

A normalização não altera caixa, pontuação, ordem ou conteúdo lexical. Portanto, ela detecta apenas diferenças de espaçamento, não similaridade semântica.

## Resultados

| Controle | Grupos | Registros envolvidos | Percentual dos registros |
| --- | ---: | ---: | ---: |
| Mesmo texto bruto e mesmo rótulo | não aplicável | {len(exact_pair_rows):,} | {percentage(len(exact_pair_rows), total)} |
| Excesso removível mantendo uma ocorrência por par exato | não aplicável | {results['exact_pair_excess']:,} | {percentage(int(results['exact_pair_excess']), total)} |
| Mesmo texto bruto, independentemente do rótulo | {results['exact_text_group_count']:,} | {len(exact_text_rows):,} | {percentage(len(exact_text_rows), total)} |
| Mesmo texto após normalizar espaços | {results['normalized_group_count']:,} | {len(normalized_rows):,} | {percentage(len(normalized_rows), total)} |
| Texto normalizado repetido com o mesmo rótulo | não aplicável | {len(same_label_rows):,} | {percentage(len(same_label_rows), total)} |
| Texto normalizado com rótulos conflitantes | {results['conflicting_group_count']:,} | {len(conflict_rows):,} | {percentage(len(conflict_rows), total)} |

## Como interpretar cada controle

### Mesmo texto e mesmo rótulo

São cópias exatas do mesmo exemplo supervisionado. Podem super-representar um padrão e causar vazamento se cópias forem distribuídas entre treino e avaliação. Remoção ainda exige uma decisão explícita.

### Mesmo texto com rótulos diferentes

É um conflito de supervisão. O mesmo conteúdo não fornece informação suficiente para escolher duas classes distintas. Esses casos exigem revisão de rótulo, contexto ou taxonomia; não devem ser resolvidos escolhendo uma classe arbitrariamente.

### Igualdade após normalização de espaços

Detecta registros cujo conteúdo difere apenas por espaços ou quebras de linha. A normalização é conservadora e usada somente para comparação.

## Arquivos de auditoria

- `exact_pair_duplicates.csv`: registros com texto bruto e rótulo exatamente iguais
- `normalized_duplicates.csv`: textos repetidos após normalização de espaços
- `conflicting_labels.csv`: textos normalizados associados a mais de um rótulo

Arquivos sem ocorrências são gerados apenas com cabeçalho. Isso documenta que o controle foi executado e encontrou zero casos.

## Limites desta etapa

- Não detecta paráfrases ou pequenas alterações lexicais.
- Não detecta cadeias de e-mail parcialmente repetidas.
- Não calcula similaridade por TF-IDF, embeddings ou distância de edição.
- Não autoriza remoção automática de registros.
- Quase duplicatas devem ser tratadas como análise posterior, separada dos controles exatos.

## Decisão antes do futuro split

Se existirem duplicatas, todas as ocorrências do mesmo grupo devem permanecer na mesma partição ou ser deduplicadas antes da divisão. Caso contrário, a avaliação poderá medir memorização em vez de generalização.
"""


def write_outputs(
    results: dict[str, object],
    output_dir: Path,
    source: Path,
    encoding: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    results["exact_pair_rows"].to_csv(
        output_dir / "exact_pair_duplicates.csv", index=False, encoding="utf-8"
    )
    results["normalized_duplicate_rows"].to_csv(
        output_dir / "normalized_duplicates.csv", index=False, encoding="utf-8"
    )
    results["conflict_rows"].to_csv(
        output_dir / "conflicting_labels.csv", index=False, encoding="utf-8"
    )
    report = build_report(results, source, encoding)
    (output_dir / "report.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"\nResultados salvos em: {output_dir.resolve()}")


def main() -> None:
    args = parse_args()
    data, encoding = read_dataset(args.input)
    validate_schema(data)
    results = audit_duplicates(data)
    write_outputs(results, args.output_dir, args.input, encoding)


if __name__ == "__main__":
    main()
