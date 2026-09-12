# ADR-008 — Auditoria e congelamento do candidato de entrega

- Status: aceito
- Data: 2026-09-11
- Commit auditado: `f85c404d112717c125114b6fbdd604c4e20748eb`

## Contexto

O executor final isolado já estava implementado e coberto por testes sintéticos. Antes de
autorizar a abertura do conjunto final de 200 tickets, era necessário demonstrar que o
projeto podia ser instalado, treinado, testado e iniciado fora do ambiente de desenvolvimento,
além de confirmar que os fluxos comuns não conhecem o caminho do teste final.

## Decisão

O commit acima é a base funcional do release candidate. A avaliação final permanece proibida
até uma autorização explícita e separada. Nenhuma métrica ou previsão sobre `test.csv` foi
produzida nesta auditoria.

Foram adotados os seguintes gates:

1. clonar o commit auditado em um diretório limpo;
2. criar um ambiente virtual novo e instalar `.[interface]` a partir do `pyproject.toml`;
3. executar `pip check`;
4. executar somente `ticket-train`, que usa treino e validação congelados;
5. comparar contagens, hashes, vocabulário e métricas de validação;
6. executar a suíte automatizada completa;
7. iniciar a interface e verificar o endpoint de saúde;
8. auditar estaticamente as referências ao teste final;
9. confirmar a ausência de `artifacts/final/`.

## Evidências

- instalação editável com dependências da interface: aprovada;
- `pip check`: nenhuma dependência quebrada;
- treino: 38.109 registros;
- validação: 9.528 registros;
- vocabulário TF-IDF: 8.544 termos;
- accuracy de validação: `0.8571578505457599`;
- macro-F1 de validação: `0.8617016202371395`;
- weighted-F1 de validação: `0.8576483790122832`;
- acesso ao teste registrado pelo treino: `false`;
- suíte: 43 testes aprovados;
- Streamlit: processo iniciado e endpoint `/_stcore/health` respondeu HTTP 200 com `ok`;
- artefatos finais: ausentes.

A varredura estática confirmou que o caminho e o hash do teste final existem no código de
execução apenas em `ticket_classifier.final_evaluation`. As demais ocorrências são testes de
isolamento, documentação e metadados do split. Treino, inferência e interface não importam o
módulo de avaliação final.

## Correção decorrente da auditoria

O README foi atualizado de 38 para 43 testes e passou a indicar que o próximo passo exige
autorização separada. `*.egg-info/` foi incluído no `.gitignore`, pois a instalação editável
gera esses metadados e eles não fazem parte do produto.

## Consequências

O projeto está pronto para o gate irreversível da avaliação final. A partir do congelamento,
qualquer mudança funcional invalida o candidato e exige repetir esta auditoria. Após abrir o
teste final, os resultados devem ser apenas reportados: não será permitido ajustar modelo,
features, pesos, limiar ou justificativa em resposta às métricas finais.
