# Modelagem

Os experimentos usam exclusivamente os conjuntos congelados de treino e validação. O teste final de 200 tickets permanece isolado.

## Experimentos

| Experimento | Mudança controlada | Accuracy | Macro-F1 |
| --- | --- | ---: | ---: |
| E01 | TF-IDF de unigramas, sem pesos | 0,8537 | 0,8534 |
| E02 | E01 + `class_weight="balanced"` | 0,8527 | 0,8558 |
| E03 | E01 + bigramas | 0,8479 | 0,8405 |
| E04 | E01 + pesos moderados | 0,8572 | 0,8617 |

## Estrutura

- `experiments/e01_unigram`: baseline textual e auditoria de erros/features;
- `experiments/e02_balanced`: efeito isolado de pesos balanceados e auditoria específica dos novos erros;
- `experiments/e03_bigrams`: efeito isolado de unigramas + bigramas;
- `experiments/e04_moderate_weights`: pesos intermediários, auditoria e candidato final;
- `requirements.txt`: dependências compartilhadas.

Cada experimento possui script, documentação, relatório e artefatos próprios. Modelos `joblib` são regeneráveis e não são versionados.

## Estado da decisão

E03 foi rejeitado porque aumentou a dimensionalidade e piorou macro-F1. E04 apresentou o melhor equilíbrio e foi selecionado como candidato final da fase de desenvolvimento. Nenhum modelo foi avaliado no teste final.
