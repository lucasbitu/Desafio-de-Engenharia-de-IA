# Etapa 4 - Divisão dos dados

Esta etapa cria uma divisão reproduzível e proporcionalmente estratificada do dataset:

- 200 tickets congelados para teste final;
- 20% dos registros restantes para validação;
- demais registros para treino.

O script não modifica o CSV original e não realiza transformação textual ou treinamento. A busca por quase duplicatas foi omitida deliberadamente devido ao prazo e permanece registrada como limitação no relatório gerado.

## Execução

A partir da raiz do repositório:

```powershell
py -3 data_split\create_splits.py
```

Para substituir conscientemente uma execução existente:

```powershell
py -3 data_split\create_splits.py --force
```

## Saídas

O diretório `outputs` recebe `train.csv`, `validation.csv`, `test.csv`, `split_manifest.csv` e `split_metadata.json`. O arquivo `report.md` registra decisões, resultados, validações, hashes e limitações.

## Controles

O script valida hash, esquema, completude, IDs únicos, teste com 200 tickets, presença das oito classes, ausência de sobreposição, preservação dos registros, reprodutibilidade e leitura dos arquivos salvos.

