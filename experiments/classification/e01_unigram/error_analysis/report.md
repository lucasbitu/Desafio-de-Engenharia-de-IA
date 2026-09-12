# Auditoria de erros e features do E01

## Escopo

Esta auditoria utiliza somente os artefatos de validação do `E01_tfidf_unigram_logreg`. O teste final não foi acessado.

## Visão geral

- Registros de validação: **9,528**
- Erros: **1,394**
- Taxa de erro: **14.63%**
- Erros com confiança a partir de 0,90: **65**
- Falsos positivos direcionados a `Hardware`: **649**

## Taxa de erro por classe real

| actual_class | total | errors | error_rate |
| --- | --- | --- | --- |
| Administrative rights | 351 | 114 | 0.3248 |
| Internal Project | 422 | 98 | 0.2322 |
| Storage | 553 | 103 | 0.1863 |
| Miscellaneous | 1406 | 222 | 0.1579 |
| Access | 1419 | 211 | 0.1487 |
| Purchase | 491 | 70 | 0.1426 |
| HR Support | 2174 | 308 | 0.1417 |
| Hardware | 2712 | 268 | 0.0988 |

## Principais pares de confusão

| actual_class | predicted_class | count | mean_confidence | max_confidence |
| --- | --- | --- | --- | --- |
| HR Support | Hardware | 192 | 0.5528 | 0.9575 |
| Miscellaneous | Hardware | 131 | 0.5277 | 0.9734 |
| Access | Hardware | 109 | 0.5514 | 0.9792 |
| Hardware | HR Support | 107 | 0.5818 | 0.9997 |
| Administrative rights | Hardware | 88 | 0.5721 | 0.9316 |
| Hardware | Miscellaneous | 82 | 0.5221 | 0.8886 |
| HR Support | Miscellaneous | 72 | 0.5891 | 0.9783 |
| Miscellaneous | HR Support | 62 | 0.5624 | 0.9196 |
| Storage | Hardware | 59 | 0.5195 | 0.9358 |
| Access | HR Support | 52 | 0.5868 | 0.9609 |
| Hardware | Access | 44 | 0.6030 | 0.9908 |
| Access | Miscellaneous | 44 | 0.5701 | 0.9712 |
| Internal Project | HR Support | 43 | 0.4997 | 0.9040 |
| Purchase | Hardware | 40 | 0.5901 | 0.9916 |
| HR Support | Access | 30 | 0.5585 | 0.9194 |

## Qualidade por faixa de confiança

| confidence_band | total | errors | mean_confidence | accuracy | error_rate |
| --- | --- | --- | --- | --- | --- |
| below_0.60 | 2202 | 911 | 0.4659 | 0.5863 | 0.4137 |
| 0.60_to_0.75 | 1356 | 279 | 0.6752 | 0.7942 | 0.2058 |
| 0.75_to_0.90 | 1720 | 139 | 0.8301 | 0.9192 | 0.0808 |
| 0.90_to_1.00 | 4250 | 65 | 0.9727 | 0.9847 | 0.0153 |

As faixas descrevem associação entre confiança e acerto, mas não constituem calibração probabilística formal.

## Features prioritárias para revisão humana

O controle abaixo prioriza features entre as 15 maiores de cada classe que aparecem em pelo menos 10 falsos positivos ou cuja precisão, condicionada à presença da feature e à previsão daquela classe, fica abaixo de 70%.

| class | feature | coefficient | validation_documents_with_feature | false_positives_with_feature | precision_when_feature_and_prediction |
| --- | --- | --- | --- | --- | --- |
| HR Support | access | 6.1861 | 1879 | 110 | 0.8284 |
| Miscellaneous | add | 7.6525 | 890 | 88 | 0.7684 |
| HR Support | oracle | 6.9571 | 769 | 71 | 0.8341 |
| Miscellaneous | change | 9.6979 | 783 | 57 | 0.8527 |
| HR Support | error | 7.7000 | 897 | 41 | 0.8901 |
| Hardware | phone | 4.2544 | 415 | 29 | 0.8688 |
| Miscellaneous | approve | 7.5555 | 270 | 28 | 0.8228 |
| Access | user | 10.2158 | 520 | 26 | 0.9055 |
| HR Support | time | 7.9785 | 294 | 26 | 0.8926 |
| Miscellaneous | name | 5.2175 | 630 | 26 | 0.8452 |
| HR Support | leave | 7.5362 | 504 | 25 | 0.9290 |
| HR Support | submit | 5.3938 | 336 | 25 | 0.9104 |
| Miscellaneous | owner | 4.8816 | 255 | 25 | 0.8092 |
| Hardware | laptop | 7.2307 | 381 | 24 | 0.9298 |
| Hardware | call | 3.4670 | 248 | 23 | 0.8639 |

Uma feature nessa lista não deve ser removida automaticamente. Ela indica onde revisar contexto, vocabulário compartilhado, boilerplate ou possíveis particularidades da taxonomia.

## Hipótese para E02

O E01 apresenta maior taxa de erro em `Administrative rights` e direciona parte relevante dos erros para `Hardware`. O E02 deve alterar somente `class_weight=None` para `class_weight="balanced"` e manter todos os demais parâmetros. A hipótese é que pesos balanceados aumentarão o recall das classes menores e reduzirão a absorção por `Hardware`.

## Critério de decisão

Macro-F1 continuará sendo a métrica principal. Também deverão ser comparados recall e F1 das classes menores, precisão de `Hardware`, quantidade de falsos positivos direcionados a `Hardware` e acurácia geral. O teste final continuará isolado.
