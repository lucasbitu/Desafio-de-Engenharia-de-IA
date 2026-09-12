# Auditoria do E01

Esta etapa audita o baseline `E01_tfidf_unigram_logreg` exclusivamente sobre a validação.

## Execução

```powershell
py -3 experiments\classification\e01_unigram\error_analysis\analyze.py
```

Use `--force` para substituir uma execução anterior.

## Saídas

- `report.md`: síntese e interpretação dos resultados;
- `outputs/error_rate_by_class.csv`: erros por classe real;
- `outputs/confusion_pairs.csv`: pares classe real versus previsão;
- `outputs/confidence_bands.csv`: qualidade por faixa de confiança;
- `outputs/confident_errors.csv`: 100 erros de maior confiança;
- `outputs/confusion_examples.csv`: exemplos dos principais pares de confusão;
- `outputs/feature_audit.csv`: comportamento das principais features na validação;
- `outputs/audit_metadata.json`: entradas, hashes, parâmetros e controles.

O script não conhece nem carrega o conjunto de teste final.
