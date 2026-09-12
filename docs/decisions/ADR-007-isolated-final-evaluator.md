# ADR-007: Executor final isolado

> Contexto histórico: este ADR registra o gate anterior à execução real. A avaliação final foi posteriormente autorizada e concluída; consulte `docs/reports/final-evaluation.md`.


## Status

Aceita para testes sintéticos. Execução real ainda não autorizada.

## Data

11 de setembro de 2026.

## Contexto

O ADR-004 exige um avaliador final separado, explícito e de uso único antes da abertura dos
200 tickets. O E04, o limiar de confiança, a justificativa e as partições já estão congelados.

## Decisão

Implementar `ticket_classifier.metrics.final_evaluation` como único fluxo autorizado a conhecer a
partição final. O módulo não é importado por treinamento de desenvolvimento, inferência ou
Streamlit e não realiza leitura ao ser importado.

A execução exige um token literal de confirmação. Ela valida hashes, contagens, colunas,
classes, identificadores, linhas de origem e ausência de sobreposição antes do treinamento.
O modelo é ajustado sobre treino mais validação com a fábrica canônica do E04, recalculando
os pesos moderados sobre o conjunto combinado.

Os resultados são escritos primeiro em diretório temporário e movidos apenas depois de todas
as verificações. Um diretório final existente nunca é sobrescrito.

## Artefatos contratados

- `model.joblib`;
- `final_metrics.json`;
- `final_predictions.csv`;
- `confusion_matrix.csv`;
- `run_metadata.json`.

Os metadados registram hashes das entradas e do modelo, commit, horário UTC, ambiente,
classes, pesos, vocabulário, quantidade de treino combinado e confirmação de roundtrip.

## Proteção contra retroalimentação

O executor não contém busca de hiperparâmetros, seleção de modelo ou ajuste de limiar. A
saída final não pode ser sobrescrita. Depois da execução real, resultados devem ser reportados
sem modificar features, pesos, limiar, justificativa ou partições.

## Validação antes do teste real

Os testes do executor usam somente CSVs sintéticos temporários e verificam:

- confirmação obrigatória;
- conjunto completo de artefatos;
- treino combinado;
- recusa de sobrescrita;
- falha fechada para hash incorreto;
- rejeição de sobreposição;
- limpeza do staging em caso de falha.

O arquivo real `test.csv` não deve ser carregado durante essa validação.

## Próximo gate

Executar toda a suíte, revisar o executor, atualizar o README com o comando final e criar um
commit de release candidate. Somente depois desse commit poderá ser considerada a autorização
separada para a avaliação única dos 200 tickets.
