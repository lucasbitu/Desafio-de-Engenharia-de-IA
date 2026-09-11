# Decisão após o E02

## Resultado

O E02 alterou somente `class_weight=None` para `class_weight="balanced"`, preservando treino, validação, TF-IDF, vocabulário, regularização, solver e seed do E01.

| Métrica | E01 | E02 | Delta |
| --- | ---: | ---: | ---: |
| Accuracy | 0,8537 | 0,8527 | -0,0009 |
| Macro-F1 | 0,8534 | 0,8558 | +0,0025 |
| Macro precision | 0,8959 | 0,8392 | -0,0567 |
| Macro recall | 0,8209 | 0,8787 | +0,0578 |
| Weighted-F1 | 0,8540 | 0,8534 | -0,0006 |

O E02 aumentou macro-F1 em aproximadamente 0,25 ponto percentual e reduziu os falsos positivos direcionados a `Hardware` de 649 para 367. Em contrapartida, produziu 1.403 erros, contra 1.394 no E01.

Na comparação registro a registro:

- ambos acertaram 7.775 tickets;
- ambos erraram 1.044 tickets;
- o E02 corrigiu 350 erros do E01;
- o E02 introduziu 359 erros novos;
- saldo líquido: 9 erros adicionais.

## Efeito por classe

Os maiores ganhos de recall ocorreram em:

- `Administrative rights`: 0,6752 para 0,8917;
- `Internal Project`: 0,7678 para 0,9336;
- `Storage`: 0,8137 para 0,9204.

Entretanto, `Administrative rights` perdeu precisão de 0,9046 para 0,6645. O E02 passou a classificar 111 tickets reais de `Hardware` como `Administrative rights`. O ganho de recall veio acompanhado de muitos falsos positivos.

`Hardware` aumentou precisão de 0,7902 para 0,8574, mas perdeu recall de 0,9012 para 0,8138. Esse comportamento confirma que os pesos balanceados deslocaram as fronteiras de decisão para as classes menores.

## Interpretação

O E02 confirma a hipótese de que pesos balanceados reduzem a dominância da classe majoritária e aumentam a cobertura das classes menores. Porém, a alteração troca precisão por recall de maneira agressiva, sobretudo em `Administrative rights`.

O ganho de macro-F1 é pequeno e fica próximo do limiar previamente definido como diferença mínima relevante. Accuracy e weighted-F1 não melhoraram. Portanto, os resultados ainda não justificam declarar o E02 vencedor definitivo.

## Decisão

Manter E01 e E02 como candidatos válidos. Não acessar o teste final e não selecionar ainda o modelo definitivo.

O próximo experimento deve avaliar unigramas e bigramas mantendo inicialmente `class_weight=None`. Isso testa se contexto lexical adicional reduz ambiguidades como `admin rights`, `password reset`, `access card` e `disk space` sem confundir o efeito com balanceamento. Depois, a mesma representação poderá ser avaliada com pesos balanceados.
