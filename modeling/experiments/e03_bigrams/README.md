# E03 - TF-IDF com unigramas e bigramas

O E03 mantém a configuração do E01 e altera somente `ngram_range` de `(1, 1)` para `(1, 2)`. Pesos de classe continuam desativados.

## Execução

```powershell
py -3 modeling\experiments\e03_bigrams\train.py
```

Use `--force` para substituir uma execução anterior. O teste final não é carregado.
