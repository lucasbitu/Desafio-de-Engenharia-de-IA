# Auditoria de erros e features do E04

## Escopo

Esta auditoria utiliza somente artefatos de validação do `E04_tfidf_unigram_logreg_moderate_weights` e os compara aos artefatos de validação de E01 e E02. O teste final não foi acessado.

## Comparação operacional

| model | total_errors | hardware_false_positives | administrative_rights_false_positives | high_confidence_errors |
| --- | --- | --- | --- | --- |
| E01 | 1394 | 649 | 25 | 65 |
| E02 | 1403 | 367 | 158 | 54 |
| E04 | 1361 | 498 | 73 | 52 |

## Comparação registro a registro

| Resultado | E04 vs E01 | E04 vs E02 |
| --- | --- | --- |
| Ambos corretos | 7978 | 7962 |
| Ambos errados | 1205 | 1198 |
| Corrigidos pelo E04 | 189 | 205 |
| Introduzidos pelo E04 | 156 | 163 |

## Taxa de erro por classe real

| actual_class | total | errors | error_rate |
| --- | --- | --- | --- |
| Administrative rights | 351 | 74 | 0.2108 |
| HR Support | 2174 | 344 | 0.1582 |
| Miscellaneous | 1406 | 198 | 0.1408 |
| Access | 1419 | 194 | 0.1367 |
| Hardware | 2712 | 366 | 0.1350 |
| Internal Project | 422 | 55 | 0.1303 |
| Purchase | 491 | 62 | 0.1263 |
| Storage | 553 | 68 | 0.1230 |

## Principais pares de confusão

| actual_class | predicted_class | count | mean_confidence | max_confidence |
| --- | --- | --- | --- | --- |
| HR Support | Hardware | 175 | 0.5095 | 0.9414 |
| Hardware | HR Support | 113 | 0.5568 | 0.9996 |
| Hardware | Miscellaneous | 105 | 0.5108 | 0.9079 |
| Miscellaneous | Hardware | 103 | 0.4937 | 0.9487 |
| HR Support | Miscellaneous | 94 | 0.5526 | 0.9784 |
| Access | Hardware | 86 | 0.5290 | 0.9682 |
| Hardware | Access | 58 | 0.5660 | 0.9890 |
| Miscellaneous | HR Support | 52 | 0.5472 | 0.9149 |
| Administrative rights | Hardware | 51 | 0.5496 | 0.8781 |
| Access | HR Support | 47 | 0.5683 | 0.9572 |
| Access | Miscellaneous | 47 | 0.5539 | 0.9713 |
| Hardware | Administrative rights | 45 | 0.5310 | 0.8688 |
| Storage | Hardware | 36 | 0.4961 | 0.8816 |
| HR Support | Access | 34 | 0.5628 | 0.9220 |
| Purchase | Hardware | 31 | 0.5364 | 0.9842 |

## Qualidade por faixa de confiança

| confidence_band | total | errors | mean_confidence | accuracy | error_rate |
| --- | --- | --- | --- | --- | --- |
| below_0.60 | 2450 | 960 | 0.4583 | 0.6082 | 0.3918 |
| 0.60_to_0.75 | 1353 | 225 | 0.6758 | 0.8337 | 0.1663 |
| 0.75_to_0.90 | 1617 | 124 | 0.8307 | 0.9233 | 0.0767 |
| 0.90_to_1.00 | 4108 | 52 | 0.9733 | 0.9873 | 0.0127 |

As faixas medem associação entre confiança e acerto, não calibração formal.

## Features prioritárias para revisão

| class | feature | coefficient | validation_documents_with_feature | false_positives_with_feature | precision_when_feature_and_prediction |
| --- | --- | --- | --- | --- | --- |
| HR Support | access | 6.3379 | 1879 | 99 | 0.8395 |
| Miscellaneous | add | 7.6863 | 890 | 90 | 0.7692 |
| HR Support | oracle | 6.6027 | 769 | 65 | 0.8434 |
| Miscellaneous | change | 9.7788 | 783 | 61 | 0.8440 |
| HR Support | error | 7.7443 | 897 | 41 | 0.8889 |
| Miscellaneous | approve | 7.4938 | 270 | 32 | 0.8000 |
| Access | user | 10.3502 | 520 | 31 | 0.8897 |
| Miscellaneous | name | 5.3291 | 630 | 29 | 0.8314 |
| Access | account | 9.1463 | 323 | 25 | 0.8879 |
| HR Support | time | 7.7765 | 294 | 25 | 0.8954 |
| Miscellaneous | ticket | 6.9293 | 364 | 24 | 0.8049 |
| Miscellaneous | owner | 4.7895 | 255 | 24 | 0.8168 |
| Internal Project | code | 13.3053 | 534 | 23 | 0.9112 |
| Internal Project | project | 9.3569 | 469 | 23 | 0.9017 |
| Administrative rights | install | 5.5576 | 211 | 23 | 0.6349 |

Features são sinais para revisão, não candidatas automáticas à remoção.
