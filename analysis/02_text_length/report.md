# Etapa 2 - Comprimento dos textos

## Objetivo

Medir o tamanho dos tickets em caracteres e palavras, identificar as caudas da distribuição e selecionar exemplos extremos para revisão humana. Esta etapa não remove, limita nem transforma tickets.

## Método

- Arquivo analisado: `all_tickets_processed_improved_v3.csv`
- Codificação utilizada: `utf-8`
- Registros analisados: **47,837**
- Caracteres: medidos após remover espaços externos e colapsar sequências de espaços
- Palavras: sequências de caracteres separadas por espaços
- Percentis: interpolação linear padrão do pandas

A normalização de espaços é usada somente para medir comprimentos. Ela não altera o CSV original.

## Estatísticas gerais

| Métrica | Caracteres | Palavras |
| --- | --- | --- |
| Mínimo | 7 | 2 |
| P01 | 37 | 6 |
| P05 | 60 | 10 |
| P25 | 110 | 17 |
| Mediana | 175 | 26 |
| Média | 291.87 | 43.60 |
| P75 | 304 | 46 |
| P95 | 926 | 136 |
| P99 | 1,932.64 | 284 |
| Máximo | 7,015 | 981 |
| Desvio padrão | 388.17 | 56.74 |

## Textos extremos

| Critério | Quantidade | Percentual |
| --- | --- | --- |
| Até 3 palavras | 49 | 0.10% |
| Até 20 caracteres | 57 | 0.12% |
| A partir do P99 de caracteres (1,932.64) | 479 | 1.00% |
| A partir do P99 de palavras (284) | 482 | 1.01% |

Os limites de 3 palavras e 20 caracteres são critérios de auditoria, não regras de exclusão. O P99 descreve a cauda superior observada e também não representa um corte automático.

## Comprimento por classe

| Classe | Tickets | Mediana caracteres | P95 caracteres | Mediana palavras | P95 palavras |
| --- | --- | --- | --- | --- | --- |
| Hardware | 13617 | 206 | 1,303.20 | 32 | 192 |
| Administrative rights | 1760 | 201 | 1,080.10 | 30 | 152 |
| Purchase | 2464 | 209 | 549.20 | 30 | 75 |
| Miscellaneous | 7060 | 176 | 885.05 | 27 | 130 |
| Internal Project | 2119 | 157 | 737.20 | 24 | 109 |
| HR Support | 10915 | 159 | 801 | 24 | 116 |
| Access | 7125 | 146 | 726.60 | 22 | 105 |
| Storage | 2777 | 142 | 707.20 | 21 | 101 |

## Perguntas para revisão

1. Os tickets mais curtos ainda contêm sinais suficientes para identificar uma classe?
2. Os textos mais longos são chamados legítimos, cadeias de e-mails ou conteúdo repetido?
3. Alguma classe possui textos sistematicamente maiores ou menores?
4. O comprimento pode funcionar como um atalho indevido para prever determinada classe?
5. Existe evidência para remover ou truncar textos, ou apenas para monitorá-los?

## Limite da conclusão automática

As estatísticas descrevem a distribuição, mas não determinam o pré-processamento. O arquivo `extreme_examples.csv` deve ser revisado antes de qualquer decisão sobre remoção, truncamento ou tratamento especial.
