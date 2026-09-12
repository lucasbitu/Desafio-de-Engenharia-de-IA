# E02 - TF-IDF unigramas com pesos balanceados

## Escopo

O E02 reutiliza exatamente os mesmos 38.109 registros de treino e 9.528 de validação do E01. A única mudança de modelagem é `class_weight="balanced"`. O teste final não foi acessado.

## Comparação principal

| Experimento | Accuracy | Macro-F1 |
| --- | --- | --- |
| E01 sem pesos | 0.8537 | 0.8534 |
| E02 balanced | 0.8527 | 0.8558 |
| Delta E02 - E01 | -0.0009 | +0.0025 |

## Comparação por classe

| Classe | P E01 | P E02 | Delta P | R E01 | R E02 | Delta R | F1 E01 | F1 E02 | Delta F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Access | 0.9200 | 0.9071 | -0.0129 | 0.8513 | 0.8739 | +0.0226 | 0.8843 | 0.8902 | +0.0058 |
| Administrative rights | 0.9046 | 0.6645 | -0.2400 | 0.6752 | 0.8917 | +0.2165 | 0.7732 | 0.7616 | -0.0117 |
| HR Support | 0.8583 | 0.8894 | +0.0311 | 0.8583 | 0.8252 | -0.0331 | 0.8583 | 0.8561 | -0.0022 |
| Hardware | 0.7902 | 0.8574 | +0.0672 | 0.9012 | 0.8138 | -0.0874 | 0.8420 | 0.8350 | -0.0070 |
| Internal Project | 0.9474 | 0.8277 | -0.1196 | 0.7678 | 0.9336 | +0.1659 | 0.8482 | 0.8775 | +0.0293 |
| Miscellaneous | 0.8234 | 0.7916 | -0.0318 | 0.8421 | 0.8727 | +0.0306 | 0.8326 | 0.8302 | -0.0025 |
| Purchase | 0.9700 | 0.9130 | -0.0570 | 0.8574 | 0.8982 | +0.0407 | 0.9103 | 0.9055 | -0.0047 |
| Storage | 0.9534 | 0.8627 | -0.0907 | 0.8137 | 0.9204 | +0.1067 | 0.8780 | 0.8906 | +0.0126 |

## Erros do E02

- Total de erros: **1,403**
- Falsos positivos direcionados a `Hardware`: **367**
- Vocabulário: **8,544 features**

## Controles

| Controle | Resultado |
| --- | --- |
| train_validation_do_not_overlap | PASS |
| train_record_ids_are_unique | PASS |
| validation_record_ids_are_unique | PASS |
| class_sets_match | PASS |
| all_eight_classes_exist | PASS |
| same_vocabulary_size_as_e01 | PASS |
| class_weight_is_balanced | PASS |
| validation_predictions_have_expected_rows | PASS |
| prediction_correctness_reconciles | PASS |

## Regra de interpretação

Macro-F1 é a métrica principal. O efeito esperado é elevar recall e F1 das classes menores e reduzir a absorção por `Hardware`, aceitando apenas uma degradação coerente nas classes maiores. Nenhuma decisão deve usar o teste final.
