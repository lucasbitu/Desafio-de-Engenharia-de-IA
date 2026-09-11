# Decisão após o E04

## Resultado

E04 obteve o melhor desempenho agregado entre os quatro experimentos sem aumentar o vocabulário nem alterar a representação textual.

| Experimento | Accuracy | Macro-F1 | Erros | FP Hardware | FP Administrative rights | Erros confiança >= 0,90 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E01 | 0,8537 | 0,8534 | 1.394 | 649 | 25 | 65 |
| E02 | 0,8527 | 0,8558 | 1.403 | 367 | 158 | 54 |
| E03 | 0,8479 | 0,8405 | 1.449 | 717 | não auditado | não auditado |
| E04 | 0,8572 | 0,8617 | 1.361 | 498 | 73 | 52 |

## Comparação por classe

Em relação ao E01, E04 aumentou F1 em:

- `Administrative rights`: +0,0171;
- `Internal Project`: +0,0288;
- `Storage`: +0,0243;
- `Hardware`: +0,0025;
- `Access`: +0,0024.

As perdas foram pequenas em `HR Support` (-0,0010), `Miscellaneous` (-0,0012) e `Purchase` (-0,0062).

## Comparação registro a registro

Contra E01, E04 corrigiu 189 erros e introduziu 156, ganho líquido de 33 acertos. Contra E02, corrigiu 205 erros e introduziu 163, ganho líquido de 42 acertos.

## Interpretação

E01 favorece excessivamente `Hardware`. E02 corrige essa dominância, mas amplia demais as classes menores, sobretudo `Administrative rights`. Os pesos moderados do E04 mantêm parte do ganho de recall das classes menores sem reproduzir a queda severa de precisão do E02.

`install` ainda merece atenção em `Administrative rights`: aparece associado a 23 falsos positivos e apresenta precisão condicionada de 0,6349. Entretanto, esse problema é menor que no E02, no qual a mesma feature esteve associada a 40 falsos positivos e precisão de 0,5000.

## Decisão

Selecionar E04 como candidato final da fase de desenvolvimento e congelar sua configuração:

- TF-IDF de unigramas;
- `min_df=2`;
- frequência sublinear;
- norma L2;
- Logistic Regression com `C=1.0` e solver `lbfgs`;
- pesos por classe `sqrt(N / (K * n_k))`, normalizados para peso médio por amostra igual a 1;
- seed 42.

O teste final permanece isolado. Antes de avaliá-lo, a configuração deverá ser registrada no ADR de seleção final e incorporada ao pipeline reutilizável de inferência e justificativa.
