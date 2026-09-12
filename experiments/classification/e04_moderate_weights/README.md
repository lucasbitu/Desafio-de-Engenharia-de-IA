# E04 - Pesos moderados por classe

O E04 mantém o TF-IDF de unigramas e a Logistic Regression do E01. A única mudança é a aplicação de pesos moderados por classe.

Para cada classe `k`, o peso inicial é:

```text
sqrt(N / (K * n_k))
```

Os pesos são normalizados para que o peso médio por amostra de treino seja 1, preservando a comparabilidade de `C=1.0`.

## Execução

```powershell
py -3 experiments\classification\e04_moderate_weights\train.py
```

Use `--force` para substituir uma execução anterior. O teste final não é carregado.
