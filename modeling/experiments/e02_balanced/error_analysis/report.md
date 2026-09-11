# Auditoria de erros e features do E02

## Escopo

Esta auditoria utiliza somente os artefatos de validação do `E02_tfidf_unigram_logreg_balanced`. O teste final não foi acessado.

## Comparação com E01

| Métrica | E01 | E02 | Delta |
| --- | --- | --- | --- |
| Total de erros | 1394 | 1403 | +9 |
| Falsos positivos em Hardware | 649 | 367 | -282 |
| Erros com confiança >= 0,90 | 65 | 54 | -11 |

O E02 possui **158** falsos positivos direcionados a `Administrative rights`; **111** vieram de `Hardware`.

## Taxa de erro por classe real

| actual_class | total | errors | error_rate |
| --- | --- | --- | --- |
| Hardware | 2712 | 505 | 0.1862 |
| HR Support | 2174 | 380 | 0.1748 |
| Miscellaneous | 1406 | 179 | 0.1273 |
| Access | 1419 | 179 | 0.1261 |
| Administrative rights | 351 | 38 | 0.1083 |
| Purchase | 491 | 50 | 0.1018 |
| Storage | 553 | 44 | 0.0796 |
| Internal Project | 422 | 28 | 0.0664 |

## Principais pares de confusão

| actual_class | predicted_class | count | mean_confidence | max_confidence |
| --- | --- | --- | --- | --- |
| HR Support | Hardware | 157 | 0.4490 | 0.9193 |
| Hardware | Miscellaneous | 136 | 0.4889 | 0.9183 |
| Hardware | HR Support | 117 | 0.5251 | 0.9994 |
| Hardware | Administrative rights | 111 | 0.5497 | 0.9462 |
| HR Support | Miscellaneous | 102 | 0.5456 | 0.9756 |
| Miscellaneous | Hardware | 72 | 0.4457 | 0.9013 |
| Access | Hardware | 68 | 0.4802 | 0.9449 |
| Hardware | Access | 66 | 0.5519 | 0.9845 |
| Access | Miscellaneous | 48 | 0.5383 | 0.9669 |
| Miscellaneous | HR Support | 42 | 0.5210 | 0.8991 |
| HR Support | Access | 37 | 0.5507 | 0.9106 |
| Access | HR Support | 36 | 0.5793 | 0.9448 |
| HR Support | Internal Project | 35 | 0.5372 | 0.9680 |
| HR Support | Storage | 30 | 0.5325 | 0.9902 |
| Hardware | Storage | 29 | 0.5032 | 0.9174 |

## Qualidade por faixa de confiança

| confidence_band | total | errors | mean_confidence | accuracy | error_rate |
| --- | --- | --- | --- | --- | --- |
| below_0.60 | 2806 | 1010 | 0.4462 | 0.6401 | 0.3599 |
| 0.60_to_0.75 | 1317 | 218 | 0.6774 | 0.8345 | 0.1655 |
| 0.75_to_0.90 | 1582 | 121 | 0.8294 | 0.9235 | 0.0765 |
| 0.90_to_1.00 | 3823 | 54 | 0.9734 | 0.9859 | 0.0141 |

As faixas medem associação entre confiança e acerto, não calibração probabilística formal.

## Features prioritárias para revisão

| class | feature | coefficient | validation_documents_with_feature | false_positives_with_feature | precision_when_feature_and_prediction |
| --- | --- | --- | --- | --- | --- |
| Miscellaneous | add | 7.5317 | 890 | 93 | 0.7663 |
| HR Support | access | 6.3377 | 1879 | 88 | 0.8516 |
| Miscellaneous | change | 9.5782 | 783 | 64 | 0.8392 |
| Administrative rights | issues | 7.6889 | 618 | 50 | 0.5370 |
| HR Support | oracle | 6.0613 | 769 | 50 | 0.8728 |
| Administrative rights | install | 5.9862 | 211 | 40 | 0.5000 |
| HR Support | error | 7.4246 | 897 | 38 | 0.8959 |
| Internal Project | code | 14.1300 | 534 | 36 | 0.8723 |
| Access | user | 10.1312 | 520 | 35 | 0.8776 |
| Internal Project | project | 9.7475 | 469 | 35 | 0.8622 |
| Miscellaneous | approve | 7.1618 | 270 | 34 | 0.7888 |
| Miscellaneous | name | 5.2273 | 630 | 33 | 0.8103 |
| Miscellaneous | owner | 4.6396 | 255 | 28 | 0.7895 |
| Hardware | si | 2.9430 | 324 | 28 | 0.8363 |
| Miscellaneous | ticket | 6.6618 | 364 | 27 | 0.7857 |

Uma feature listada não deve ser removida automaticamente. O objetivo é identificar vocabulário compartilhado e mudanças causadas pelos pesos.

## Interpretação

O balanceamento reduz a absorção por `Hardware`, mas desloca erros para classes menores, sobretudo `Administrative rights`. A decisão deve considerar a troca entre recall e precisão, a quantidade de erros confiantes e a coerência semântica dos novos falsos positivos.
