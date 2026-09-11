# ADR-002: Seleção do modelo final da fase de desenvolvimento

## Status

Aceita.

## Data

11 de setembro de 2026.

## Contexto

O ADR-001 definiu TF-IDF de palavras com Logistic Regression como metodologia principal para classificar os tickets. Após essa decisão, o dataset foi dividido de forma estratificada e reproduzível em:

- 38.109 tickets de treino;
- 9.528 tickets de validação;
- 200 tickets reservados para o teste final.

Os 200 tickets de teste foram isolados antes da modelagem e não foram carregados, inspecionados nem usados nos experimentos descritos neste documento.

Esta decisão seleciona a configuração que seguirá para o pipeline reutilizável de inferência e justificativa. Ela não registra desempenho final de teste e não autoriza ainda o acesso à amostra de 200 tickets.

## Critério de seleção

Macro-F1 foi definida como métrica principal porque as oito classes possuem distribuição desigual. Accuracy, weighted-F1, métricas por classe, quantidade e destino dos erros e confiança das previsões foram usados como evidências complementares.

A seleção seguiu estes princípios:

1. alterar uma dimensão principal por experimento;
2. usar os mesmos conjuntos de treino e validação;
3. manter seed 42;
4. ajustar TF-IDF somente no treino;
5. não consultar o teste para selecionar modelo ou parâmetros;
6. analisar erros e features, não apenas métricas agregadas;
7. preferir a configuração mais simples quando diferenças fossem irrelevantes.

## Experimentos considerados

### E01: baseline textual

- TF-IDF de unigramas;
- `min_df=2`;
- frequência sublinear;
- norma L2;
- Logistic Regression;
- `C=1.0`;
- solver `lbfgs`;
- sem pesos de classe.

O E01 estabeleceu que o texto contém sinal classificatório forte e superou claramente o baseline da classe majoritária.

### E02: pesos balanceados

O E02 preservou a configuração do E01 e alterou somente `class_weight` para `"balanced"`.

O balanceamento elevou o recall das classes menores e reduziu a quantidade de falsos positivos direcionados a `Hardware`. Entretanto, ampliou excessivamente algumas classes menores, principalmente `Administrative rights`, cuja precisão caiu de 0,9046 para 0,6645.

### E03: unigramas e bigramas

O E03 preservou a ausência de pesos do E01 e alterou somente `ngram_range` de `(1, 1)` para `(1, 2)`.

O vocabulário aumentou de 8.544 para 143.673 features, incluindo 135.129 bigramas. Apesar de aprender expressões úteis, o experimento piorou macro-F1, acurácia e desempenho em sete das oito classes. O E03 foi rejeitado.

### E04: pesos moderados

O E04 preservou a representação e o classificador do E01 e aplicou pesos intermediários por classe.

Para cada classe `k`, o peso inicial foi calculado como:

```text
sqrt(N / (K * n_k))
```

Onde:

- `N` é o número de tickets de treino;
- `K` é o número de classes;
- `n_k` é o número de tickets da classe `k` no treino.

Os pesos foram normalizados para que o peso médio por amostra de treino fosse igual a 1. Essa normalização preserva a escala global dos pesos e permite comparar `C=1.0` com os experimentos anteriores sem alterar indiretamente a força média da regularização.

## Resultados de validação

| Experimento | Accuracy | Macro-F1 | Erros |
| --- | ---: | ---: | ---: |
| E01 - unigramas, sem pesos | 0,8537 | 0,8534 | 1.394 |
| E02 - pesos balanceados | 0,8527 | 0,8558 | 1.403 |
| E03 - unigramas e bigramas | 0,8479 | 0,8405 | 1.449 |
| E04 - pesos moderados | **0,8572** | **0,8617** | **1.361** |

O E04 obteve simultaneamente:

- maior macro-F1;
- maior acurácia;
- menor número total de erros;
- menor número de erros com confiança a partir de 0,90;
- melhor equilíbrio entre falsos positivos em `Hardware` e `Administrative rights`.

## Resultados por classe

| Classe | F1 E01 | F1 E02 | F1 E04 |
| --- | ---: | ---: | ---: |
| Access | 0,8843 | 0,8902 | 0,8867 |
| Administrative rights | 0,7732 | 0,7616 | 0,7903 |
| HR Support | 0,8583 | 0,8561 | 0,8573 |
| Hardware | 0,8420 | 0,8350 | 0,8445 |
| Internal Project | 0,8482 | 0,8775 | 0,8769 |
| Miscellaneous | 0,8326 | 0,8302 | 0,8314 |
| Purchase | 0,9103 | 0,9055 | 0,9041 |
| Storage | 0,8780 | 0,8906 | 0,9023 |

Em relação ao E01, o E04 melhorou F1 em cinco classes. As perdas em `HR Support`, `Miscellaneous` e `Purchase` foram pequenas e não anularam os ganhos nas classes menores.

## Auditoria dos erros

| Modelo | Erros | FP em Hardware | FP em Administrative rights | Erros com confiança >= 0,90 |
| --- | ---: | ---: | ---: | ---: |
| E01 | 1.394 | 649 | 25 | 65 |
| E02 | 1.403 | 367 | 158 | 54 |
| E04 | **1.361** | 498 | 73 | **52** |

Contra o E01, o E04 corrigiu 189 erros e introduziu 156, produzindo ganho líquido de 33 acertos. Contra o E02, corrigiu 205 erros e introduziu 163, produzindo ganho líquido de 42 acertos.

O E04 mantém 498 falsos positivos direcionados a `Hardware`, menos que o E01, e 73 direcionados a `Administrative rights`, menos que a metade do E02. Isso confirma que os pesos moderados reduziram os dois extremos observados.

## Análise de confiança

No E04:

| Faixa de confiança | Registros | Erros | Acurácia |
| --- | ---: | ---: | ---: |
| Abaixo de 0,60 | 2.450 | 960 | 0,6082 |
| 0,60 a 0,75 | 1.353 | 225 | 0,8337 |
| 0,75 a 0,90 | 1.617 | 124 | 0,9233 |
| 0,90 a 1,00 | 4.108 | 52 | 0,9873 |

Essas faixas demonstram associação entre confiança e acerto, mas não constituem calibração probabilística formal. As probabilidades serão apresentadas como confiança estimada do modelo, não como garantia estatística.

## Features e riscos remanescentes

As features com maior associação a falsos positivos incluem termos compartilhados entre classes, como `access`, `add`, `oracle`, `change`, `error`, `user` e `install`.

`install` permanece um risco para `Administrative rights`. No E04, a feature aparece associada a 23 falsos positivos e apresenta precisão condicionada de 0,6349. Esse resultado é melhor que o E02, em que esteve associada a 40 falsos positivos e precisão condicionada de 0,5000.

Essas features não serão removidas manualmente. Sua exclusão poderia eliminar sinais legítimos, criar regras específicas para a validação e dificultar a generalização. O risco será documentado e observado na avaliação final.

## Decisão

Selecionar o E04 como configuração final da fase de desenvolvimento.

A configuração congelada é:

- entrada: coluna `Document`;
- alvo: coluna `Topic_group`;
- TF-IDF de palavras;
- minúsculas habilitadas;
- unigramas, `ngram_range=(1, 1)`;
- `min_df=2`;
- norma L2;
- frequência sublinear;
- tipo numérico `float64`;
- Logistic Regression multiclasse;
- `C=1.0`;
- solver `lbfgs`;
- `max_iter=1000`;
- seed 42;
- pesos moderados calculados a partir das frequências do conjunto usado no treinamento;
- pesos normalizados para média ponderada por amostra igual a 1.

## Consequências

### Consequências positivas

- melhora macro-F1 e acurácia em relação aos demais candidatos;
- mantém explicabilidade por coeficientes e contribuições locais;
- reduz a dominância de `Hardware` sem a sobrecorreção do E02;
- preserva o vocabulário compacto de 8.544 features na fase de desenvolvimento;
- mantém treinamento e inferência locais e reproduzíveis;
- não depende de LLM para decidir a classe.

### Trade-offs aceitos

- alguns tickets continuam semanticamente ambíguos;
- classes compartilham vocabulário;
- `Administrative rights` ainda possui a maior taxa de erro;
- probabilidades não estão formalmente calibradas;
- quase duplicatas semânticas não foram auditadas;
- o dataset aparenta ter sido previamente processado;
- entradas brutas da interface podem diferir do padrão do treino.

## Próximas etapas autorizadas

Esta decisão autoriza:

1. transformar a configuração do E04 em pipeline reutilizável;
2. implementar contrato validado de entrada e saída;
3. consolidar extração de evidências locais;
4. produzir justificativa determinística de uma a três sentenças;
5. adicionar testes automatizados;
6. criar a interface interativa;
7. verificar a execução completa em ambiente reproduzível.

## Condições antes do teste final

O teste final de 200 tickets só poderá ser acessado depois que:

- o pipeline reutilizável estiver concluído;
- a configuração acima estiver aplicada sem alterações;
- o modelo puder ser salvo e recarregado;
- a justificativa determinística estiver validada;
- os testes automatizados estiverem aprovados;
- a interface estiver funcional;
- os comandos de execução estiverem documentados;
- o hash ou versão do pipeline final estiver registrado.

Após essas condições, o modelo poderá ser treinado conforme o protocolo final definido e avaliado uma única vez nos 200 tickets. Os resultados do teste não deverão ser usados para reabrir a seleção ou ajustar hiperparâmetros.

## Critérios para reconsideração futura

Esta decisão poderá ser revista em uma versão posterior ao desafio se houver:

- novos dados rotulados;
- textos brutos com melhor qualidade;
- mudança de taxonomia;
- requisitos de custo ou latência incompatíveis;
- evidência de drift;
- avaliação controlada demonstrando ganho material com embeddings;
- necessidade operacional de privilegiar recall ou precisão de uma classe específica.

Nenhuma dessas condições autoriza alterar o modelo antes da avaliação final prevista para esta entrega.

## Evidências

- `modeling/experiments/e01_unigram/report.md`;
- `modeling/experiments/e01_unigram/error_analysis/report.md`;
- `modeling/experiments/e02_balanced/report.md`;
- `modeling/experiments/e02_balanced/error_analysis/report.md`;
- `modeling/experiments/e03_bigrams/report.md`;
- `modeling/experiments/e03_bigrams/decision.md`;
- `modeling/experiments/e04_moderate_weights/report.md`;
- `modeling/experiments/e04_moderate_weights/error_analysis/report.md`;
- `modeling/experiments/e04_moderate_weights/decision.md`.
