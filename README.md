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
- testes automatizados do núcleo;
- interface interativa Streamlit;
- reprodução aprovada em ambiente virtual limpo;
- executor final isolado validado com dados sintéticos;
- release candidate `release-candidate-v1` auditado e congelado;
- avaliação única dos 200 tickets finais concluída;
- relatório final de teste publicado.

O teste final foi aberto uma única vez depois do congelamento do release candidate. Seus
resultados não foram usados para alterar o modelo ou qualquer decisão de desenvolvimento.

## Arquitetura

```text
Ticket
  -> validação e normalização mínima
  -> TF-IDF de unigramas
  -> Logistic Regression com pesos moderados
  -> classe e confiança estimada
  -> contribuições locais positivas
  -> política de baixa confiança
  -> justificativa determinística de segurança
  -> reescrita opcional por LLM
       -> válida: linguagem natural apoiada nas evidências
       -> erro ou saída inválida: fallback determinístico
  -> JSON {"class": "...", "justification": "..."}
```

O classificador é a única autoridade sobre a classe. O LLM é uma camada opcional de
apresentação: não pode mudar previsão, confiança ou evidências, e a aplicação continua
funcional sem credenciais ou disponibilidade do provedor.

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

No teste final congelado de 200 tickets, após treinamento em treino mais validação, obteve
accuracy 0,9050, macro-F1 0,9135 e weighted-F1 0,9061. Consulte o
[relatório final](docs/final-evaluation-report.md).

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

Para instalar também a interface:

```powershell
.venv\Scripts\python -m pip install -e ".[interface]"
```

Para instalar interface e reescrita generativa opcional:

```powershell
.venv\Scripts\python -m pip install -e ".[delivery]"
```

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

Os testes pressupõem que `ticket-train` tenha gerado os artefatos oficiais em
`artifacts/development/`. Eles não dependem dos binários históricos ignorados em
`modeling/experiments/`.

## Interface interativa

Depois de executar `ticket-train`:

```powershell
.venv\Scripts\streamlit run app.py
```

A interface reutiliza `DeliveryPredictionService`, exibe a classe e a justificativa no
contrato público exigido e oferece diagnósticos de confiança opcionais. Ela não carrega
datasets, não calcula métricas e não conhece o caminho do teste final.

Por padrão, a justificativa permanece determinística. Para ativar somente a reescrita:

```powershell
$env:ENABLE_LLM_JUSTIFICATION="true"
$env:OPENAI_API_KEY="sua-chave"
$env:OPENAI_MODEL="gpt-5-mini"
.venv\Scripts\streamlit run app.py
```

A chamada usa a Responses API sem armazenamento da resposta (`store=false`). O LLM recebe
apenas classe, confiança, indicador de baixa confiança, evidências permitidas e o fallback.
Saída sem a classe, sem evidência permitida, longa demais ou sem alerta obrigatório é
rejeitada e substituída automaticamente pela justificativa determinística.

## Docker

A imagem instala as dependências, reproduz o modelo de desenvolvimento durante o build e
inicia o Streamlit na porta 8501:

```powershell
docker compose up --build
```

A aplicação ficará disponível em `http://localhost:8501`. Para ativar o LLM no Compose,
defina `ENABLE_LLM_JUSTIFICATION=true`, `OPENAI_API_KEY` e, opcionalmente, `OPENAI_MODEL`
no ambiente antes do comando. A chave não é copiada para a imagem; ela é passada somente em
tempo de execução.

## Reprodução em ambiente limpo

O candidato de entrega foi auditado em uma cópia local limpa com um ambiente virtual novo.
A instalação declarada, o treinamento de desenvolvimento, o `pip check`, os 43 testes e o
smoke test do Streamlit foram aprovados. Accuracy, macro-F1, weighted-F1, vocabulário,
classes e pesos foram reproduzidos exatamente.

O arquivo `joblib` reproduzido não teve identidade binária com o artefato anterior, apesar
de parâmetros, previsões, probabilidades e métricas equivalentes. Por isso, cada artefato de
release recebe seu próprio hash; equivalência funcional é validada separadamente.

## Avaliação final isolada

O comando abaixo é deliberadamente separado do fluxo comum e não deve ser executado durante
desenvolvimento:

```powershell
.venv\Scripts\ticket-final-evaluate --confirm I_UNDERSTAND_THIS_OPENS_THE_FINAL_TEST
```

Antes de executá-lo, deve existir um release candidate identificado, com Git limpo, 43 testes
aprovados e autorização explícita para abrir os 200 tickets. O executor valida hashes,
contagens, classes e ausência de sobreposição; treina o E04 em treino mais validação; recalcula
os pesos moderados; e grava modelo, métricas, previsões, matriz de confusão e metadados em
`artifacts/final/`.

O diretório final não pode existir previamente e nunca é sobrescrito. Resultados observados
nesta execução não podem retroalimentar modelo, features, pesos, limiar ou justificativa.

## Decisões arquiteturais

- [ADR-001](docs/decisions/ADR-001-classification-methodology.md): metodologia inicial.
- [ADR-002](docs/decisions/ADR-002-final-model-selection.md): seleção e congelamento do E04; substitui as escolhas iniciais de bigramas e balanceamento integral.
- [ADR-003](docs/decisions/ADR-003-low-confidence-policy.md): limiar de baixa confiança.
- [ADR-004](docs/decisions/ADR-004-development-baseline-and-release-gates.md): baseline e gates de release.
- [ADR-005](docs/decisions/ADR-005-thin-streamlit-interface.md): interface Streamlit fina.
- [ADR-006](docs/decisions/ADR-006-clean-environment-reproduction.md): reprodução em ambiente limpo.
- [ADR-007](docs/decisions/ADR-007-isolated-final-evaluator.md): executor final isolado.
- [ADR-008](docs/decisions/ADR-008-release-candidate-audit.md): auditoria do candidato de entrega.
- [ADR-009](docs/decisions/ADR-009-optional-llm-rewriting.md): reescrita generativa opcional sem grafo.

## Limitações conhecidas

- o dataset aparenta ter sido previamente processado;
- entradas brutas podem diferir da distribuição de treino;
- quase duplicatas semânticas não foram auditadas;
- as probabilidades não possuem calibração formal;
- baixa confiança representa incerteza, não erro;
- algumas classes compartilham vocabulário e continuam ambíguas.

## Estado de entrega

A implementação e a avaliação final estão concluídas. Antes do envio, resta somente revisar
o conteúdo do repositório e preparar a apresentação da solução; o modelo está definitivamente
congelado e não deve receber ajustes baseados no teste final.

A reescrita generativa e a conteinerização foram adicionadas depois da avaliação final como
recursos de entrega. Elas não alteram o classificador congelado e não foram avaliadas nem
ajustadas usando os 200 tickets finais.
