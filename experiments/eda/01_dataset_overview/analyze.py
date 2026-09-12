"""Etapa 1 da EDA: estrutura, completude e distribuição das classes."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd


TEXT_COLUMN = "Document"
LABEL_COLUMN = "Topic_group"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = PROJECT_ROOT.parent / "archive" / "all_tickets_processed_improved_v3.csv"
DEFAULT_REPORT = Path(__file__).with_name("report.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analisa estrutura, completude e distribuição de classes do dataset."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Caminho do CSV de tickets.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT,
        help="Caminho do relatório Markdown gerado.",
    )
    return parser.parse_args()


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


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
    required_columns = {TEXT_COLUMN, LABEL_COLUMN}
    missing_columns = sorted(required_columns - set(data.columns))

    if missing_columns:
        raise ValueError(
            "Colunas obrigatórias ausentes: "
            f"{missing_columns}. Colunas encontradas: {list(data.columns)}"
        )
    if data.empty:
        raise ValueError("O dataset não contém registros.")


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        escaped = [str(value).replace("|", "\\|").replace("\n", " ") for value in row]
        lines.append("| " + " | ".join(escaped) + " |")
    return "\n".join(lines)


def build_report(data: pd.DataFrame, source: Path, encoding: str) -> str:
    row_count, column_count = data.shape
    null_counts = data.isna().sum()
    blank_text_count = int(data[TEXT_COLUMN].fillna("").astype(str).str.strip().eq("").sum())
    blank_label_count = int(data[LABEL_COLUMN].fillna("").astype(str).str.strip().eq("").sum())

    class_counts = data[LABEL_COLUMN].value_counts(dropna=False)
    class_rows: list[list[object]] = []
    for class_name, count in class_counts.items():
        percentage = count / row_count * 100
        class_rows.append([class_name, int(count), f"{percentage:.2f}%"])

    largest_class = str(class_counts.index[0])
    largest_count = int(class_counts.iloc[0])
    smallest_class = str(class_counts.index[-1])
    smallest_count = int(class_counts.iloc[-1])
    imbalance_ratio = largest_count / smallest_count
    majority_baseline = largest_count / row_count * 100

    schema_rows = [
        [column, str(data[column].dtype), int(null_counts[column])]
        for column in data.columns
    ]
    example_text = str(data.iloc[0][TEXT_COLUMN]).replace("\n", " ")
    if len(example_text) > 240:
        example_text = example_text[:237] + "..."
    example_label = str(data.iloc[0][LABEL_COLUMN])

    return f"""# Etapa 1 - Visão geral do dataset

## Objetivo

Validar a fonte, identificar o contrato dos dados, medir a completude dos campos obrigatórios e descrever a distribuição da variável-alvo. Esta etapa não limpa dados nem toma decisões de modelagem.

## Fonte e reprodutibilidade

- Arquivo analisado: `{source.name}`
- Tamanho: {source.stat().st_size:,} bytes
- Codificação utilizada: `{encoding}`
- SHA-256: `{calculate_sha256(source)}`

O hash identifica exatamente a versão do arquivo que originou este relatório.

## Estrutura

- Registros lógicos: **{row_count:,}**
- Colunas: **{column_count}**
- Coluna de entrada: **`{TEXT_COLUMN}`**
- Coluna-alvo: **`{LABEL_COLUMN}`**

{markdown_table(["Coluna", "Tipo", "Nulos"], schema_rows)}

## Completude

- Textos nulos ou vazios: **{blank_text_count:,}**
- Rótulos nulos ou vazios: **{blank_label_count:,}**

Não foram aplicadas remoções. Um texto preenchido ainda pode ser curto, repetitivo ou pouco informativo; isso será investigado nas etapas seguintes.

## Exemplo estrutural

- `Document`: {example_text}
- `Topic_group`: {example_label}

O conteúdo de `Document` aparenta ter sido previamente processado: o exemplo usa letras minúsculas, pouca pontuação e estrutura gramatical reduzida. Essa é uma hipótese inicial, não uma regra de limpeza.

## Distribuição das classes

{markdown_table(["Classe", "Quantidade", "Percentual"], class_rows)}

- Número de classes: **{len(class_counts)}**
- Maior classe: **{largest_class}**, com **{largest_count:,}** registros
- Menor classe: **{smallest_class}**, com **{smallest_count:,}** registros
- Razão entre maior e menor: **{imbalance_ratio:.2f}**
- Baseline da classe majoritária: **{majority_baseline:.2f}%** de acurácia

## Interpretação

O dataset é desbalanceado em termos relativos. A maior classe possui aproximadamente {imbalance_ratio:.2f} vezes mais registros que a menor, e prever sempre `{largest_class}` já produziria {majority_baseline:.2f}% de acurácia. Portanto, acurácia isolada não será suficiente em uma avaliação futura.

Apesar do desbalanceamento, a menor classe ainda possui {smallest_count:,} exemplos. Não há evidência nesta etapa para aplicar oversampling, undersampling ou pesos de classe. Essas alternativas só devem ser comparadas durante a futura modelagem.

## Decisões e limites desta etapa

- A coluna `Document` será tratada como entrada textual.
- A coluna `Topic_group` será tratada como variável-alvo.
- Nenhuma linha será removida por ausência de texto ou rótulo.
- Nenhuma transformação textual foi aplicada.
- A análise de comprimento será feita separadamente na etapa 2.
- Duplicatas, qualidade semântica e decisões de pré-processamento permanecem em aberto.
"""


def main() -> None:
    args = parse_args()
    data, encoding = read_dataset(args.input)
    validate_schema(data)
    report = build_report(data, args.input, encoding)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")

    print(report)
    print(f"\nRelatório salvo em: {args.output.resolve()}")


if __name__ == "__main__":
    main()

