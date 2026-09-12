# QuantumRise Ticket Classifier

Classificador explicável de chamados de TI desenvolvido para o desafio de Engenharia de IA da QuantumRise. O núcleo recebe o texto de um ticket, prevê uma das oito classes e produz uma justificativa determinística baseada nas features que contribuíram para a decisão.

## Estado do projeto

Concluído:

- análise exploratória reproduzível;
- divisão congelada em treino, validação e 200 tickets de teste final;
- comparação dos experimentos E00 a E04;
- seleção do E04 por macro-F1 de validação;
- pipeline reutilizável em `src/`;
- contratos validados de entrada e saída;
- evidência local por `TF-IDF x coeficiente`;
- justificativa determinística;
- política de baixa confiança selecionada somente na validação;
- treinamento oficial da fase de desenvolvimento;
- testes automatizados do núcleo.

Ainda não implementado:

- interface interativa;
- treinamento final em treino mais validação;
- avaliação única dos 200 tickets finais;
- relatório final de teste.

O `test.csv` permanece fora dos módulos de desenvolvimento e só poderá ser acessado depois do congelamento do release candidate.

## Arquitetura

```text
Ticket
  -> validação e normalização mínima
  -> TF-IDF de unigramas
  -> Logistic Regression com pesos moderados
  -> classe e confiança estimada
  -> contribuições locais positivas
  -> política de baixa confiança
  -> justificativa determinística
  -> JSON {"class": "...", "justification": "..."}
```

O classificador é a única autoridade sobre a classe. A justificativa não pode mudar a previsão nem citar evidências ausentes do texto.

## Modelo selecionado

O E04 usa:

- TF-IDF de palavras e unigramas;
- `min_df=2`;
- frequência sublinear;
- norma L2;
- `float64`;
- Logistic Regression multiclasse;
- `C=1.0`;
- solver `lbfgs`;
- `max_iter=1000`;
- seed 42;
- pesos `sqrt(N / (K * n_k))`, normalizados para peso médio por amostra igual a 1.

Na validação congelada, o E04 obteve accuracy 0,8572 e macro-F1 0,8617.

## Baixa confiança

Uma previsão é sinalizada quando:

```text
confidence < 0.60
```

O limiar é o menor candidato que capturou pelo menos 70% dos erros de validação sem sinalizar mais de 30% dos tickets. Ele sinalizou 25,71% da validação e capturou 70,54% dos erros. O alerta muda somente a redação da justificativa, nunca a classe.

## Instalação

Requer Python 3.11, 3.12 ou 3.13.

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e .
```

As versões das dependências estão fixadas em `pyproject.toml`.

## Dados congelados

O treinamento de desenvolvimento espera:

```text
data_split/outputs/train.csv
data_split/outputs/validation.csv
```

O comando valida quantidades e hashes antes de carregar os registros. Arquivos diferentes são recusados.

## Treinamento e validação de desenvolvimento

```powershell
.venv\Scripts\ticket-train
```

Alternativamente:

```powershell
.venv\Scripts\python -m ticket_classifier.training
```

O comando usa somente treino e validação e gera, em `artifacts/development/`:

- `model.joblib`;
- `validation_metrics.json`;
- `validation_predictions.csv`;
- `run_metadata.json`.

Por segurança, uma segunda execução recusa sobrescrever os artefatos. Use `--force` somente quando a substituição for intencional.

## Testes

Após instalar o pacote:

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```

Durante o desenvolvimento sem instalação:

```powershell
$env:PYTHONPATH="$PWD\src"
py -3 -m unittest discover -s tests -v
```

## Decisões arquiteturais

- [ADR-001](docs/decisions/ADR-001-classification-methodology.md): metodologia inicial.
- [ADR-002](docs/decisions/ADR-002-final-model-selection.md): seleção e congelamento do E04; substitui as escolhas iniciais de bigramas e balanceamento integral.
- [ADR-003](docs/decisions/ADR-003-low-confidence-policy.md): limiar de baixa confiança.

## Limitações conhecidas

- o dataset aparenta ter sido previamente processado;
- entradas brutas podem diferir da distribuição de treino;
- quase duplicatas semânticas não foram auditadas;
- as probabilidades não possuem calibração formal;
- baixa confiança representa incerteza, não erro;
- algumas classes compartilham vocabulário e continuam ambíguas.

## Próxima etapa

Depois de reproduzir o treinamento e executar todos os testes em ambiente limpo, o próximo bloco será a interface interativa. O teste final continuará fechado até o congelamento completo do release candidate.
