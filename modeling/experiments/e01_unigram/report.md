# Etapa 5 - Baselines de classificação

## Escopo

Esta execução usou somente treino e validação. O teste final de 200 tickets não foi carregado.

## Experimentos

- `E00_majority`: classe majoritária, sem texto.
- `E01_tfidf_unigram_logreg`: TF-IDF de unigramas com Logistic Regression sem pesos.

## Resultados na validação

| Experimento | Accuracy | Macro-F1 |
| --- | --- | --- |
| E00_majority | 0.2846 | 0.0554 |
| E01_tfidf_unigram_logreg | 0.8537 | 0.8534 |

## Desempenho por classe do E01

| Classe | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| Access | 0.9200 | 0.8513 | 0.8843 | 1419 |
| Administrative rights | 0.9046 | 0.6752 | 0.7732 | 351 |
| HR Support | 0.8583 | 0.8583 | 0.8583 | 2174 |
| Hardware | 0.7902 | 0.9012 | 0.8420 | 2712 |
| Internal Project | 0.9474 | 0.7678 | 0.8482 | 422 |
| Miscellaneous | 0.8234 | 0.8421 | 0.8326 | 1406 |
| Purchase | 0.9700 | 0.8574 | 0.9103 | 491 |
| Storage | 0.9534 | 0.8137 | 0.8780 | 553 |

## Evidências

- Vocabulário aprendido apenas no treino: **8,544 features**.
- Evidência local = valor TF-IDF x coeficiente da classe prevista.
- Apenas features presentes no ticket e com contribuição positiva são citadas.
- Nenhum LLM foi utilizado.

## Controles

| Controle | Resultado |
| --- | --- |
| train_validation_do_not_overlap | PASS |
| train_record_ids_are_unique | PASS |
| validation_record_ids_are_unique | PASS |
| class_sets_match | PASS |
| all_eight_classes_exist | PASS |

## Próxima decisão

Revisar métricas, features e erros mais confiantes. Depois, comparar separadamente pesos balanceados e bigramas.
