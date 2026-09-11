# Análise exploratória dos dados

Esta pasta organiza a EDA em etapas pequenas, reproduzíveis e fáceis de explicar. Cada etapa terá sua própria pasta com:

- um arquivo Python contendo somente os cálculos daquela etapa;
- um `report.md` gerado pelo próprio código;
- conclusões limitadas às evidências calculadas.

## Etapas

| Etapa | Objetivo | Estado |
| --- | --- | --- |
| `01_dataset_overview` | Validar arquivo, esquema, completude e distribuição das classes | Concluída |
| `02_text_length` | Analisar comprimentos e textos extremos | Concluída |
| `03_duplicates` | Investigar duplicatas exatas e conflitos de rótulo | Concluída |

**Estado da fase:** concluída nas três etapas acima. Decisões de pré-processamento e modelagem estão fora do escopo deste ciclo.

Uma etapa só deve ser criada quando a anterior estiver compreendida. O CSV original não será modificado por nenhum script de análise.

## Dependências

Instale as dependências da EDA:

```powershell
py -3 -m pip install -r analysis\requirements.txt
```

## Execução da etapa 1

A partir da raiz do repositório:

```powershell
py -3 analysis\01_dataset_overview\analyze.py
```

Para informar outro CSV:

```powershell
py -3 analysis\01_dataset_overview\analyze.py --input "C:\caminho\tickets.csv"
```

## Execução da etapa 2

```powershell
py -3 analysis\02_text_length\analyze.py
```

O script gera `analysis/02_text_length/report.md` e `analysis/02_text_length/extreme_examples.csv`. A execução deve ser feita pelo responsável pela análise; os resultados serão interpretados antes de avançar para duplicatas.

## Execução da etapa 3

```powershell
py -3 analysis\03_duplicates\analyze.py
```

O script gera `analysis/03_duplicates/report.md` e arquivos CSV de auditoria. A comparação normalizada altera somente espaços para detectar diferenças de formatação; ela não modifica o dataset original.
