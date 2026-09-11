# ADR-003: Política de baixa confiança

## Status

Aceita.

## Data

11 de setembro de 2026.

## Contexto

O ADR-002 congelou o E04 como modelo final da fase de desenvolvimento e registrou que suas probabilidades representam confiança estimada, não garantia estatística de acerto. Esta decisão define como sinalizar previsões frágeis sem alterar a classe escolhida pelo modelo.

O teste final de 200 tickets não foi carregado, inspecionado nem utilizado. Toda a análise abaixo usa exclusivamente as 9.528 previsões de validação do E04.

## Critério operacional

Selecionar o menor limiar da grade que simultaneamente:

- capture pelo menos 70% dos erros de validação;
- sinalize no máximo 30% dos tickets.

A grade foi congelada antes da seleção:

```text
0,40; 0,45; 0,50; 0,55; 0,60; 0,65; 0,70
```

## Resultados

| Limiar | Sinalizados | Taxa sinalizada | Erros capturados | Captura de erros | Acurácia abaixo | Acurácia no restante |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0,40 | 667 | 7,00% | 336 | 24,69% | 49,63% | 88,43% |
| 0,45 | 1.076 | 11,29% | 518 | 38,06% | 51,86% | 90,03% |
| 0,50 | 1.517 | 15,92% | 686 | 50,40% | 54,78% | 91,57% |
| 0,55 | 2.009 | 21,09% | 842 | 61,87% | 58,09% | 93,10% |
| 0,60 | 2.450 | 25,71% | 960 | 70,54% | 60,82% | 94,33% |
| 0,65 | 2.911 | 30,55% | 1.051 | 77,22% | 63,90% | 95,32% |
| 0,70 | 3.332 | 34,97% | 1.123 | 82,51% | 66,30% | 96,16% |

O limiar de 0,60 é o primeiro que atende aos dois critérios. O candidato seguinte captura mais erros, mas sinaliza 30,55% dos tickets e ultrapassa o limite operacional estabelecido.

## Decisão

Definir baixa confiança como:

```text
confidence < 0.60
```

Uma confiança exatamente igual a 0,60 não será sinalizada.

## Comportamento

A política:

- preserva sempre a classe prevista pelo E04;
- adiciona `low_confidence` somente ao diagnóstico interno;
- mantém o contrato público com apenas `class` e `justification`;
- usa linguagem cautelosa na justificativa quando a confiança está abaixo do limiar;
- não afirma que uma previsão sinalizada está errada;
- não interpreta a confiança como probabilidade calibrada;
- não consulta LLM nem cria uma segunda rota de classificação.

## Consequências

### Positivas

- 25,71% da validação concentra 70,54% dos erros;
- a região não sinalizada alcança 94,33% de acurácia observada;
- a interface poderá recomendar revisão humana de forma consistente;
- o valor e o critério podem ser reproduzidos a partir do artefato de validação.

### Limitações

- 401 erros de validação permanecem acima ou iguais ao limiar;
- 1.490 previsões sinalizadas estão corretas;
- o alerta significa incerteza, não erro;
- não foi realizada calibração probabilística formal;
- o desempenho do limiar pode mudar diante de drift ou textos brutos diferentes do dataset.

## Condição de congelamento

O limiar não poderá ser alterado depois da abertura do teste final de 200 tickets. Seu resultado no teste deverá ser reportado como evidência final, não usado para reajustar esta decisão.
