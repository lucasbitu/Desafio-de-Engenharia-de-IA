# Decisão após o E03

## Resultado

O E03 alterou somente `ngram_range=(1, 1)` para `(1, 2)`, preservando dados, Logistic Regression, ausência de pesos, regularização, solver e seed do E01.

| Métrica | E01 | E03 | Delta |
| --- | ---: | ---: | ---: |
| Accuracy | 0,8537 | 0,8479 | -0,0058 |
| Macro-F1 | 0,8534 | 0,8405 | -0,0129 |
| Erros | 1.394 | 1.449 | +55 |
| Falsos positivos em Hardware | 649 | 717 | +68 |

O vocabulário cresceu de 8.544 para 143.673 features. Destas, 135.129 são bigramas.

## Efeito por classe

O F1 piorou em sete das oito classes. A única melhoria foi `HR Support`, de 0,8583 para 0,8597, diferença insuficiente para compensar as perdas restantes.

As maiores quedas ocorreram em:

- `Administrative rights`: -0,0466 de F1;
- `Internal Project`: -0,0197;
- `Purchase`: -0,0141;
- `Storage`: -0,0123.

Bigramas semanticamente úteis apareceram entre as features, incluindo `access card`, `password reset`, `new starter`, `annual leave`, `purchase request` e `shared mailbox`. Entretanto, também surgiram sequências ligadas a estilo ou boilerplate, como `hi please`, `code thank`, `please log` e `requested by`.

## Interpretação

Com `min_df=2`, o uso irrestrito de bigramas introduziu dimensionalidade excessiva e muitos padrões raros. A Logistic Regression distribuiu capacidade entre 143.673 features sem ganho de generalização. O aumento de falsos positivos em `Hardware` mostra que o contexto adicional não resolveu a principal confusão do E01.

## Decisão

Rejeitar E03 como candidato final. Não acessar o teste final.

E01 e E02 permanecem candidatos. Se bigramas forem reconsiderados, deverá ser em um experimento distinto com controle de dimensionalidade, como `min_df` maior, limite de features ou regularização mais forte. Isso não deve ser tratado como continuação automática: primeiro deve ser comparado ao valor de concluir o fluxo de justificativa e interface dentro do prazo.
