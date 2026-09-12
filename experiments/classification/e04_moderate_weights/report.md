# E04 - TF-IDF com pesos moderados

## Escopo

O E04 usa os mesmos conjuntos e a mesma configuração do E01. A única mudança é a aplicação de pesos por classe iguais à raiz quadrada dos pesos balanceados, normalizados para peso médio por amostra igual a 1. O teste final não foi acessado.

## Comparação principal

| Experimento | Accuracy | Macro-F1 |
| --- | --- | --- |
| E01 | 0.8537 | 0.8534 |
| E02 | 0.8527 | 0.8558 |
| E03 | 0.8479 | 0.8405 |
| E04 | 0.8572 | 0.8617 |
| Delta E04 - E01 | +0.0035 | +0.0083 |

## E01 versus E04 por classe

| Classe | P E01 | P E04 | R E01 | R E04 | F1 E01 | F1 E04 | Delta F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Access | 0.9200 | 0.9115 | 0.8513 | 0.8633 | 0.8843 | 0.8867 | +0.0024 |
| Administrative rights | 0.9046 | 0.7914 | 0.6752 | 0.7892 | 0.7732 | 0.7903 | +0.0171 |
| HR Support | 0.8583 | 0.8735 | 0.8583 | 0.8418 | 0.8583 | 0.8573 | -0.0010 |
| Hardware | 0.7902 | 0.8249 | 0.9012 | 0.8650 | 0.8420 | 0.8445 | +0.0025 |
| Internal Project | 0.9474 | 0.8843 | 0.7678 | 0.8697 | 0.8482 | 0.8769 | +0.0288 |
| Miscellaneous | 0.8234 | 0.8053 | 0.8421 | 0.8592 | 0.8326 | 0.8314 | -0.0012 |
| Purchase | 0.9700 | 0.9367 | 0.8574 | 0.8737 | 0.9103 | 0.9041 | -0.0062 |
| Storage | 0.9534 | 0.9291 | 0.8137 | 0.8770 | 0.8780 | 0.9023 | +0.0243 |

## Pesos aplicados

| Classe | Peso |
| --- | --- |
| Access | 0.977253 |
| Administrative rights | 1.966320 |
| HR Support | 0.789575 |
| Hardware | 0.706892 |
| Internal Project | 1.792016 |
| Miscellaneous | 0.981673 |
| Purchase | 1.661759 |
| Storage | 1.565437 |

## Erros e complexidade

- Total de erros: **1,361**
- Falsos positivos em `Hardware`: **498**
- Falsos positivos em `Administrative rights`: **73**
- Erros com confiança a partir de 0,90: **52**
- Vocabulário: **8,544 features**

## Controles

| Controle | Resultado |
| --- | --- |
| train_validation_do_not_overlap | PASS |
| train_record_ids_are_unique | PASS |
| validation_record_ids_are_unique | PASS |
| class_sets_match | PASS |
| all_eight_classes_exist | PASS |
| ngram_range_remains_unigram | PASS |
| custom_class_weights_are_applied | PASS |
| sample_weight_mean_is_one | PASS |
| weights_are_between_e01_and_e02_extremes | PASS |
| same_vocabulary_size_as_e01 | PASS |
| validation_predictions_have_expected_rows | PASS |
| prediction_correctness_reconciles | PASS |
