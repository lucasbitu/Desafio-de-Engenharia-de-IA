# E02 - Logistic Regression com pesos balanceados

O E02 mantém a configuração do E01 e altera somente `class_weight` de `None` para `"balanced"`.

## Execução

```powershell
py -3 modeling\experiments\e02_balanced\train.py
```

Use `--force` para substituir uma execução anterior.

## Regra de decisão

Macro-F1 é a métrica principal. A comparação também observa métricas por classe, acurácia e falsos positivos direcionados a `Hardware`. O teste final não é carregado.
