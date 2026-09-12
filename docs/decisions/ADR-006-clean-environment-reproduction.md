# ADR-006: Reprodução em ambiente limpo

## Status

Aceita.

## Data

11 de setembro de 2026.

## Contexto

O ADR-004 exige que instalação, treinamento de desenvolvimento, testes e interface sejam
reproduzidos em ambiente limpo antes do acesso único aos 200 tickets finais. O ADR-005 define
essa reprodução como o próximo gate depois da interface Streamlit.

## Procedimento

A validação utilizou uma cópia local limpa do commit `7f33473` e um ambiente virtual novo.
Foram executados, nesta ordem:

1. instalação do pacote somente a partir do `pyproject.toml`, com o extra `interface`;
2. verificação de dependências com `pip check`;
3. treinamento E04 de desenvolvimento usando somente `train.csv`;
4. avaliação somente em `validation.csv`;
5. comparação de hashes de entrada, configuração, classes, pesos, vocabulário e métricas;
6. execução da suíte automatizada;
7. inicialização do Streamlit em modo headless;
8. consulta ao endpoint local de saúde;
9. verificação de ausência de acesso ao teste final pelo fluxo comum.

Nenhuma previsão ou métrica foi calculada sobre `test.csv`.

## Defeito encontrado

Na primeira execução, quatro grupos de testes dependeram de artefatos históricos ignorados
pelo Git em `modeling/experiments/e04_moderate_weights/outputs/`. Esses arquivos existiam no
ambiente de desenvolvimento, mas não em um clone limpo.

A correção centralizou os caminhos oficiais de desenvolvimento em `config.py`. Interface e
testes passaram a consumir exclusivamente os artefatos reproduzíveis gerados por
`ticket-train` em `artifacts/development/`.

A alteração não modifica representação textual, hiperparâmetros, pesos, classes, política de
confiança, justificativa ou partições.

## Resultados

O treinamento limpo reproduziu:

| Controle | Resultado |
| --- | ---: |
| Registros de treino | 38.109 |
| Registros de validação | 9.528 |
| Vocabulário | 8.544 |
| Accuracy | 0,8571578505457599 |
| Macro-F1 | 0,8617016202371395 |
| Weighted-F1 | 0,8576483790122832 |
| Testes automatizados | 38 aprovados |
| Smoke test Streamlit | HTTP 200, corpo `ok` |
| Dependências quebradas | 0 |

Após a correção, os 38 testes também foram aprovados no ambiente de desenvolvimento.

## Identidade binária do modelo

O artefato `joblib` produzido na reprodução teve hash diferente do artefato anterior. Apesar
disso, parâmetros, classes, pesos, vocabulário, previsões, probabilidades e métricas foram
equivalentes, e o roundtrip de persistência preservou as previsões.

Decide-se tratar o SHA-256 do arquivo como identidade de uma instância de artefato, não como
prova isolada de equivalência matemática entre treinamentos. Cada modelo final deverá registrar
seu próprio hash, acompanhado de controles funcionais e metadados do ambiente.

## Decisão

Considerar aprovado o gate de reprodução limpa após incorporar a correção de portabilidade em
um commit identificável. O próximo gate é implementar e testar o executor final isolado sem
executá-lo ainda contra `test.csv`.

## Consequências

- o procedimento documentado funciona sem artefatos experimentais locais;
- os testes passam a verificar o mesmo modelo usado pela interface;
- o teste final permanece fora do desenvolvimento;
- o hash do modelo continua obrigatório, mas é interpretado junto de equivalência funcional;
- qualquer alteração posterior no núcleo exige nova reprodução limpa antes da avaliação final.
