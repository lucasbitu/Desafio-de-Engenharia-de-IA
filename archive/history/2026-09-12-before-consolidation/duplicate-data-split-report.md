# Etapa 4 - Divisão reproduzível dos dados

## Objetivo

Reservar exatamente 200 tickets para a avaliação final e dividir os demais registros em treino e validação sem alterar o dataset original.

## Fonte

- Arquivo: `all_tickets_processed_improved_v3.csv`
- Codificação: `utf-8`
- SHA-256: `044FDACE33FA564E1E60453F2941DAFC95539C99878B0D32746950394B9DD4D4`
- Registros: **47,837**

## Decisões

- O teste final foi separado antes de treino e validação.
- O teste contém exatamente **200 tickets**.
- A seleção é proporcionalmente estratificada por `Topic_group`.
- A seed é **42**.
- O conjunto de desenvolvimento foi dividido em **80% treino** e **20% validação**.
- As cotas inteiras foram calculadas pelo método dos maiores restos.
- Cada linha recebeu um `record_id` SHA-256 derivado da versão do dataset, linha de origem, texto e rótulo.
- O CSV original não foi modificado e os textos não foram transformados.
- A auditoria de quase duplicatas não foi executada devido ao prazo disponível.

## Distribuição resultante

| Topic_group | train | validation | test | total |
| --- | ---: | ---: | ---: | ---: |
| Access | 5676 | 1419 | 30 | 7125 |
| Administrative rights | 1402 | 351 | 7 | 1760 |
| HR Support | 8695 | 2174 | 46 | 10915 |
| Hardware | 10848 | 2712 | 57 | 13617 |
| Internal Project | 1688 | 422 | 9 | 2119 |
| Miscellaneous | 5625 | 1406 | 29 | 7060 |
| Purchase | 1963 | 491 | 10 | 2464 |
| Storage | 2212 | 553 | 12 | 2777 |
| TOTAL | 38109 | 9528 | 200 | 47837 |

## Validações

- `test_has_exact_requested_size`: **PASS**
- `all_rows_are_assigned`: **PASS**
- `all_source_ids_are_preserved`: **PASS**
- `train_validation_do_not_overlap`: **PASS**
- `train_test_do_not_overlap`: **PASS**
- `validation_test_do_not_overlap`: **PASS**
- `all_classes_exist_in_train`: **PASS**
- `all_classes_exist_in_validation`: **PASS**
- `all_classes_exist_in_test`: **PASS**
- `record_ids_remain_unique`: **PASS**

- `same_seed_reproduces_same_assignment`: **PASS**
- `saved_files_can_be_read_back`: **PASS**

## Arquivos gerados

- `train.csv`: ajuste do TF-IDF e da Logistic Regression.
- `validation.csv`: desenvolvimento e análise de erros.
- `test.csv`: amostra final congelada de 200 tickets.
- `split_manifest.csv`: associação entre registro e partição.
- `split_metadata.json`: parâmetros, contagens, hashes e limitações.

### SHA-256 dos artefatos

- `train.csv`: `62DA11CE58FA9EAF6C3AC04A77BE24FC0C66A97864829D68CA98FDBE6FDDF894`
- `validation.csv`: `4EEA86B63A3E3D7186C6F52C3FFF41D6D8E266679D7B9496428E3E2971366DB0`
- `test.csv`: `E857B8873DE34B47EC39360F82BD25A04497A811D9D985E835F9D1EEF27F5B6D`
- `split_manifest.csv`: `87C2F449476ADB89EC47230881E8246E1F8FC4AA796EC1C9D4182105E1E49C23`

## Uso correto

O TF-IDF deve executar `fit` somente sobre `train.csv`. Validação e teste devem receber apenas `transform`. Depois de congelar as decisões com a validação, o pipeline poderá ser retreinado em treino mais validação e avaliado uma única vez no teste final.

Os 200 tickets não devem ser substituídos nem regenerados silenciosamente. Uma nova execução sem `--force` recusa sobrescrever os artefatos existentes.

## Limitação aceita

A EDA encontrou zero duplicatas exatas, zero duplicatas após normalização conservadora de espaços e zero conflitos determinísticos. Não foi realizada busca por paráfrases, pequenas alterações lexicais ou cadeias de e-mail parcialmente compartilhadas. Portanto, permanece possível que quase duplicatas atravessem as partições e inflem parcialmente as métricas. Esse risco foi aceito e documentado para concluir a etapa dentro do prazo.
