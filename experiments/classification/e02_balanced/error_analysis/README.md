# Auditoria do E02

Esta etapa audita o `E02_tfidf_unigram_logreg_balanced` exclusivamente sobre a validação e compara seu perfil de erros com a auditoria do E01.

## Execução

```powershell
py -3 experiments\classification\e02_balanced\error_analysis\analyze.py
```

Use `--force` para substituir uma execução anterior. O teste final não é carregado.

## Saídas

- `report.md`: síntese e interpretação;
- `outputs/error_rate_by_class.csv`;
- `outputs/confusion_pairs.csv`;
- `outputs/confidence_bands.csv`;
- `outputs/confident_errors.csv`;
- `outputs/confusion_examples.csv`;
- `outputs/feature_audit.csv`;
- `outputs/audit_metadata.json`.
