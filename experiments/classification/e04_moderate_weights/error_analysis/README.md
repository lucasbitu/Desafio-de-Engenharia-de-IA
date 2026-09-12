# Auditoria do E04

Auditoria do `E04_tfidf_unigram_logreg_moderate_weights` exclusivamente sobre a validação, usando os mesmos controles das auditorias E01 e E02.

## Execução

```powershell
py -3 experiments\classification\e04_moderate_weights\error_analysis\analyze.py
```

Use `--force` para substituir uma execução anterior. O teste final não é carregado.
