# E03 - TF-IDF com unigramas e bigramas

## Escopo

O E03 usa os mesmos 38.109 registros de treino e 9.528 de validação. A única mudança em relação ao E01 é `ngram_range=(1, 2)`. `class_weight` permanece `None`. O teste final não foi acessado.

## Comparação principal

| Experimento | Accuracy | Macro-F1 |
| --- | --- | --- |
| E01 unigramas | 0.8537 | 0.8534 |
| E02 unigramas balanced | 0.8527 | 0.8558 |
| E03 unigramas + bigramas | 0.8479 | 0.8405 |
| Delta E03 - E01 | -0.0058 | -0.0129 |

## E01 versus E03 por classe

| Classe | P E01 | P E03 | R E01 | R E03 | F1 E01 | F1 E03 | Delta F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Access | 0.9200 | 0.9301 | 0.8513 | 0.8351 | 0.8843 | 0.8801 | -0.0043 |
| Administrative rights | 0.9046 | 0.9251 | 0.6752 | 0.5983 | 0.7732 | 0.7266 | -0.0466 |
| HR Support | 0.8583 | 0.8499 | 0.8583 | 0.8698 | 0.8583 | 0.8597 | +0.0014 |
| Hardware | 0.7902 | 0.7747 | 0.9012 | 0.9089 | 0.8420 | 0.8364 | -0.0056 |
| Internal Project | 0.9474 | 0.9537 | 0.7678 | 0.7322 | 0.8482 | 0.8284 | -0.0197 |
| Miscellaneous | 0.8234 | 0.8248 | 0.8421 | 0.8371 | 0.8326 | 0.8309 | -0.0017 |
| Purchase | 0.9700 | 0.9670 | 0.8574 | 0.8350 | 0.9103 | 0.8962 | -0.0141 |
| Storage | 0.9534 | 0.9708 | 0.8137 | 0.7812 | 0.8780 | 0.8657 | -0.0123 |

## Complexidade e erros

- Vocabulário total: **143,673 features**
- Bigramas no vocabulário: **135,129**
- Erros do E03: **1,449**
- Falsos positivos direcionados a `Hardware`: **717**

## Controles

| Controle | Resultado |
| --- | --- |
| train_validation_do_not_overlap | PASS |
| train_record_ids_are_unique | PASS |
| validation_record_ids_are_unique | PASS |
| class_sets_match | PASS |
| all_eight_classes_exist | PASS |
| ngram_range_is_one_to_two | PASS |
| class_weight_remains_none | PASS |
| vocabulary_contains_bigrams | PASS |
| validation_predictions_have_expected_rows | PASS |
| prediction_correctness_reconciles | PASS |

## Interpretação esperada

Bigramas preservam contexto lexical como `admin rights`, `password reset` e `disk space`, mas aumentam dimensionalidade e podem aprender boilerplate. A decisão deve considerar macro-F1, efeito por classe, erros e legibilidade das evidências. O teste final continua isolado.
