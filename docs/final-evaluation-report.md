# Relatório da avaliação final

## Protocolo

A avaliação foi executada uma única vez em 2026-09-12 (UTC), após autorização explícita,
sobre o commit congelado `0a15f4f2f49ff314ae88d4b4e8141f00faa35639`, identificado pela
tag local `release-candidate-v1`.

O modelo E04 foi treinado novamente na união de treino e validação, totalizando 47.637
tickets. O conjunto final tinha 200 tickets e seu hash SHA-256 foi validado antes do
carregamento. Não houve sobreposição entre as partições. Nenhuma decisão do modelo, feature,
peso, limiar ou justificativa foi modificada depois da observação destes resultados.

## Resultado global

| Métrica | Resultado |
|---|---:|
| Accuracy | 0,9050 |
| Macro-F1 | 0,9135 |
| Weighted-F1 | 0,9061 |
| Acertos | 181 |
| Erros | 19 |

O macro-F1 maior que a accuracy indica que o desempenho não ficou concentrado apenas nas
classes mais frequentes. Todas as oito classes tiveram F1 acima de 0,84 no teste final.

## Resultado por classe

| Classe | Precisão | Recall | F1 | Suporte |
|---|---:|---:|---:|---:|
| Access | 0,9310 | 0,9000 | 0,9153 | 30 |
| Administrative rights | 1,0000 | 0,8571 | 0,9231 | 7 |
| HR Support | 0,9302 | 0,8696 | 0,8989 | 46 |
| Hardware | 0,9138 | 0,9298 | 0,9217 | 57 |
| Internal Project | 1,0000 | 0,8889 | 0,9412 | 9 |
| Miscellaneous | 0,7714 | 0,9310 | 0,8438 | 29 |
| Purchase | 1,0000 | 0,9000 | 0,9474 | 10 |
| Storage | 0,9167 | 0,9167 | 0,9167 | 12 |

`Miscellaneous` teve a menor precisão porque recebeu previsões incorretas vindas de Access,
Administrative rights, HR Support, Hardware e Purchase. Isso é coerente com seu caráter
residual e com as ambiguidades observadas durante a análise de validação. A maior confusão
individual foi `HR Support -> Hardware`, com quatro casos.

## Política de baixa confiança

O limiar `confidence < 0.60`, selecionado exclusivamente na validação, apresentou:

| Indicador | Resultado |
|---|---:|
| Tickets sinalizados | 49 de 200 (24,50%) |
| Erros capturados | 16 de 19 (84,21%) |
| Accuracy abaixo do limiar | 67,35% |
| Accuracy no limiar ou acima | 98,01% |

Esses números sustentam o uso do alerta como mecanismo de triagem: cerca de um quarto dos
tickets concentra a maior parte dos erros. O alerta continua sem poder alterar a classe.

## Integridade dos artefatos

Os artefatos foram gravados em `artifacts/final/` com proteção contra sobrescrita:

| Arquivo | SHA-256 |
|---|---|
| `confusion_matrix.csv` | `EE9A5D2CFD3DC3ECDB4F8CC552C87A213CCA5573C42AF6F94C9CB5989C04A461` |
| `final_metrics.json` | `85274FA7B7C673F793A59B3425CDBD3D05E94DA8EB5CF507FCD83E3F93DD68C2` |
| `final_predictions.csv` | `A14AA8DC180CC61B01879302ED792BF8143B09271606CD5932D6F9A95221C20D` |
| `model.joblib` | `6C08847BCC6DF8BEA0BE3C04B20D49DEA76E6C8F5814AF6727D157D54FFD7C84` |
| `run_metadata.json` | `804DB53602C0EF32F0A0412FE96FE7EB7C8D96C62F7F3763A8E384500B5294B9` |

O arquivo de previsões contém 200 linhas, nenhuma célula nula e nenhum `record_id` duplicado.
O modelo recarregado do disco produziu previsões idênticas às obtidas antes da serialização.

## Conclusão

O resultado final confirma que o baseline clássico escolhido atende bem ao problema com uma
solução simples, rápida, explicável e reproduzível. O teste final está encerrado. A partir
deste ponto, qualquer evolução deve ser tratada como uma nova versão e avaliada em um novo
conjunto de teste, nunca por novos ajustes contra estes mesmos 200 tickets.
