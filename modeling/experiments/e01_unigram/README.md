# Etapa 5 - Baselines de classificação

Esta etapa compara dois experimentos usando exclusivamente os conjuntos de treino e validação:

- `E00`: classe majoritária, sem usar o texto;
- `E01`: TF-IDF de unigramas com Logistic Regression sem pesos de classe.

O teste final de 200 tickets não é carregado nem conhecido pelo script.

## Execução

```powershell
py -3 -m pip install -r modeling\requirements.txt
py -3 modeling\experiments\e01_unigram\train.py
```

Use `--force` para substituir conscientemente uma execução anterior. O modelo e as previsões completas de validação são regeneráveis e não são versionados.

## Saídas

- `outputs/validation_metrics.json`: métricas agregadas e por classe;
- `outputs/validation_predictions.csv`: previsões da validação;
- `outputs/top_features_by_class.csv`: maiores coeficientes globais por classe;
- `outputs/example_predictions.json`: uma previsão explicada por classe real;
- `outputs/run_metadata.json`: configuração, hashes e controles;
- `report.md`: síntese do experimento;
- `outputs/baseline_model.joblib`: pipeline treinado e regenerável.

Macro-F1 é a métrica principal. Esta etapa ainda não escolhe o modelo final.
