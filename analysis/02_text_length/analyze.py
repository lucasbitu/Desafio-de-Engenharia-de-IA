"""Etapa 2 da EDA: comprimento dos textos e inspeção de extremos."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


TEXT_COLUMN = "Document"
LABEL_COLUMN = "Topic_group"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT.parent / "archive" / "all_tickets_processed_improved_v3.csv"
DEFAULT_REPORT = Path(__file__).with_name("report.md")
DEFAULT_EXAMPLES = Path(__file__).with_name("extreme_examples.csv")
PERCENTILES = [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analisa comprimento em caracteres e palavras dos tickets."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--examples-output", type=Path, default=DEFAULT_EXAMPLES)
    parser.add_argument("--short-word-threshold", type=int, default=3)
    parser.add_argument("--short-character-threshold", type=int, default=20)
    parser.add_argument("--examples-per-group", type=int, default=10)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.short_word_threshold < 0:
        raise ValueError("--short-word-threshold não pode ser negativo.")
    if args.short_character_threshold < 0:
        raise ValueError("--short-character-threshold não pode ser negativo.")
    if args.examples_per_group < 1:
        raise ValueError("--examples-per-group deve ser pelo menos 1.")


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


def prepare_lengths(data: pd.DataFrame) -> pd.DataFrame:
    required_columns = {TEXT_COLUMN, LABEL_COLUMN}
    missing_columns = sorted(required_columns - set(data.columns))
    if missing_columns:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing_columns}")
    if data.empty:
        raise ValueError("O dataset não contém registros.")

    result = data[[TEXT_COLUMN, LABEL_COLUMN]].copy()
    result["normalized_text"] = (
        result[TEXT_COLUMN]
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    result["character_count"] = result["normalized_text"].str.len()
    result["word_count"] = result["normalized_text"].str.findall(r"\S+").str.len()
    return result


def descriptive_statistics(values: pd.Series) -> dict[str, float]:
    quantiles = values.quantile(PERCENTILES)
    return {
        "Mínimo": float(values.min()),
        "P01": float(quantiles.loc[0.01]),
        "P05": float(quantiles.loc[0.05]),
        "P25": float(quantiles.loc[0.25]),
        "Mediana": float(quantiles.loc[0.50]),
        "Média": float(values.mean()),
        "P75": float(quantiles.loc[0.75]),
        "P95": float(quantiles.loc[0.95]),
        "P99": float(quantiles.loc[0.99]),
        "Máximo": float(values.max()),
        "Desvio padrão": float(values.std()),
    }


def format_number(value: float) -> str:
    if value.is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}"


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        escaped = [str(value).replace("|", "\\|").replace("\n", " ") for value in row]
        lines.append("| " + " | ".join(escaped) + " |")
    return "\n".join(lines)


def select_extreme_examples(
    lengths: pd.DataFrame,
    examples_per_group: int,
) -> pd.DataFrame:
    columns = [
        "extreme_group",
        LABEL_COLUMN,
        "character_count",
        "word_count",
        TEXT_COLUMN,
    ]

    shortest = lengths.nsmallest(examples_per_group, ["word_count", "character_count"]).copy()
    shortest.insert(0, "extreme_group", "shortest")

    longest = lengths.nlargest(examples_per_group, ["character_count", "word_count"]).copy()
    longest.insert(0, "extreme_group", "longest")

    return pd.concat([shortest, longest], ignore_index=True)[columns]


def build_report(
    lengths: pd.DataFrame,
    source: Path,
    encoding: str,
    short_word_threshold: int,
    short_character_threshold: int,
) -> str:
    character_stats = descriptive_statistics(lengths["character_count"])
    word_stats = descriptive_statistics(lengths["word_count"])

    statistics_rows = [
        [metric, format_number(character_stats[metric]), format_number(word_stats[metric])]
        for metric in character_stats
    ]

    short_by_words = int(lengths["word_count"].le(short_word_threshold).sum())
    short_by_characters = int(
        lengths["character_count"].le(short_character_threshold).sum()
    )
    p99_character_cutoff = character_stats["P99"]
    p99_word_cutoff = word_stats["P99"]
    long_by_characters = int(
        lengths["character_count"].ge(p99_character_cutoff).sum()
    )
    long_by_words = int(lengths["word_count"].ge(p99_word_cutoff).sum())
    total = len(lengths)

    per_class = (
        lengths.groupby(LABEL_COLUMN)
        .agg(
            tickets=(TEXT_COLUMN, "size"),
            median_characters=("character_count", "median"),
            p95_characters=("character_count", lambda values: values.quantile(0.95)),
            median_words=("word_count", "median"),
            p95_words=("word_count", lambda values: values.quantile(0.95)),
        )
        .sort_values("median_words", ascending=False)
        .reset_index()
    )
    per_class_rows = [
        [
            row[LABEL_COLUMN],
            int(row["tickets"]),
            format_number(float(row["median_characters"])),
            format_number(float(row["p95_characters"])),
            format_number(float(row["median_words"])),
            format_number(float(row["p95_words"])),
        ]
        for _, row in per_class.iterrows()
    ]

    return f"""# Etapa 2 - Comprimento dos textos

## Objetivo

Medir o tamanho dos tickets em caracteres e palavras, identificar as caudas da distribuição e selecionar exemplos extremos para revisão humana. Esta etapa não remove, limita nem transforma tickets.

## Método

- Arquivo analisado: `{source.name}`
- Codificação utilizada: `{encoding}`
- Registros analisados: **{total:,}**
- Caracteres: medidos após remover espaços externos e colapsar sequências de espaços
- Palavras: sequências de caracteres separadas por espaços
- Percentis: interpolação linear padrão do pandas

A normalização de espaços é usada somente para medir comprimentos. Ela não altera o CSV original.

## Estatísticas gerais

{markdown_table(["Métrica", "Caracteres", "Palavras"], statistics_rows)}

## Textos extremos

| Critério | Quantidade | Percentual |
| --- | --- | --- |
| Até {short_word_threshold} palavras | {short_by_words:,} | {short_by_words / total * 100:.2f}% |
| Até {short_character_threshold} caracteres | {short_by_characters:,} | {short_by_characters / total * 100:.2f}% |
| A partir do P99 de caracteres ({format_number(p99_character_cutoff)}) | {long_by_characters:,} | {long_by_characters / total * 100:.2f}% |
| A partir do P99 de palavras ({format_number(p99_word_cutoff)}) | {long_by_words:,} | {long_by_words / total * 100:.2f}% |

Os limites de {short_word_threshold} palavras e {short_character_threshold} caracteres são critérios de auditoria, não regras de exclusão. O P99 descreve a cauda superior observada e também não representa um corte automático.

## Comprimento por classe

{markdown_table(
    ["Classe", "Tickets", "Mediana caracteres", "P95 caracteres", "Mediana palavras", "P95 palavras"],
    per_class_rows,
)}

As estatísticas descrevem a distribuição, mas não determinam o pré-processamento. O arquivo `extreme_examples.csv` deve ser revisado antes de qualquer decisão sobre remoção, truncamento ou tratamento especial.
"""


def main() -> None:
    args = parse_args()
    validate_args(args)
    data, encoding = read_dataset(args.input)
    lengths = prepare_lengths(data)

    report = build_report(
        lengths,
        args.input,
        encoding,
        args.short_word_threshold,
        args.short_character_threshold,
    )
    examples = select_extreme_examples(lengths, args.examples_per_group)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.examples_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    examples.to_csv(args.examples_output, index=False, encoding="utf-8")

    print(report)
    print(f"\nRelatório salvo em: {args.output.resolve()}")
    print(f"Exemplos extremos salvos em: {args.examples_output.resolve()}")


if __name__ == "__main__":
    main()
