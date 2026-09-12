# QuantumRise Ticket Classifier

Classificador explicável de chamados de TI desenvolvido para o QuantumRise AI Engineering Challenge. O sistema recebe o texto de um ticket, prevê uma das oito classes do dataset e retorna uma justificativa curta baseada nos sinais utilizados pelo próprio modelo.

## Objetivo

Classificar tickets de suporte de TI em uma das oito categorias exigidas pelo desafio e explicar cada decisão com evidências do próprio texto, preservando reprodutibilidade, rastreabilidade e execução local.

## Stack

Python 3.11, pandas e scikit-learn para preparação e modelagem; Pydantic para validar a saída; Joblib para persistir o pipeline; Streamlit para o teste interativo; `unittest` para os testes; e Docker para a execução reproduzível.

## Visão geral

```text
Ticket
  → validação e normalização mínima
  → vetorização TF-IDF
  → Logistic Regression
  → classe e confiança estimada
  → extração das contribuições locais
  → justificativa determinística
  → JSON final
```

O caminho oficial funciona localmente e não depende de LLM, API externa ou credenciais.

## Entrada e saída

Entrada: texto de um ticket.

Saída pública:

```json
{
  "class": "Access",
  "justification": "The terms 'password' and 'login' support the Access classification."
}
```

A aplicação também pode mostrar confiança e evidências para diagnóstico, sem alterar o contrato exigido pelo desafio.

## Como executar

### Docker

```powershell
docker compose up --build
```

Abra `http://localhost:8501`.

### Ambiente virtual

Requer Python 3.11, 3.12 ou 3.13.

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[interface]"
.venv\Scripts\ticket-train
.venv\Scripts\streamlit run interface/app.py
```

### Testes

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```

## Dados

O dataset possui 47.837 tickets nas colunas `Document` (texto) e `Topic_group` (rótulo). Foram encontradas oito classes: Access, Administrative rights, Hardware, HR Support, Internal Project, Miscellaneous, Purchase e Storage.

A distribuição é desbalanceada: `Hardware` representa 28,47% dos registros e `Administrative rights`, 3,68%. O texto aparenta ter passado por processamento anterior. Não foram encontradas duplicatas exatas ou após normalização conservadora de espaços; quase duplicatas semânticas não foram auditadas.

A EDA completa está em [`docs/reports/eda.md`](docs/reports/eda.md).

## Preparação e amostragem

O dataset original não foi alterado. A divisão usa seed 42 e mantém as proporções das classes:

| Partição | Tickets | Uso |
|---|---:|---|
| Treino | 38.109 | ajuste do modelo durante o desenvolvimento |
| Validação | 9.528 | comparação dos experimentos e escolha das decisões |
| Teste final | 200 | avaliação única do candidato congelado |

Cada registro recebeu um identificador determinístico. Os hashes, contagens, classes e ausência de sobreposição foram validados antes do treinamento e da avaliação.

Os splits ficam em `data/splits/`. O procedimento completo está em [`docs/reports/data-split.md`](docs/reports/data-split.md).

## Metodologia de classificação

O modelo selecionado usa TF-IDF de unigramas, frequência sublinear, Logistic Regression multiclasse, pesos moderados por classe e seed 42. Os pesos são proporcionais à raiz quadrada do desbalanceamento. Isso reduz a dominância das classes frequentes sem provocar a mudança agressiva de precisão para recall observada com pesos totalmente balanceados.

### Abordagem escolhida e por quê

O dataset já contém dezenas de milhares de exemplos rotulados e somente oito classes fixas. TF-IDF com Logistic Regression usa diretamente essa supervisão, treina rapidamente, funciona localmente e permite relacionar a previsão às palavras que influenciaram o classificador.

LLM, RAG e embeddings foram considerados, mas não foram adotados no caminho principal:

- um LLM acrescentaria custo, latência, variabilidade e exposição dos tickets a um serviço externo;
- RAG aumentaria a complexidade sem necessidade demonstrada para oito classes supervisionadas;
- embeddings poderiam melhorar generalização semântica, mas reduziriam a transparência direta e exigiriam uma comparação adicional. 

Além disso, os textos do dataset aparentam ter passado por pré-processamento anterior, com perda parcial de estrutura gramatical. Isso reduz parte do contexto linguístico que abordagens semânticas poderiam explorar. Em contrapartida, o grande volume de exemplos rotulados e a presença de sinais lexicais discriminativos entre as classes favorecem uma abordagem supervisionada baseada em TF-IDF.

## Seleção do modelo

As configurações abaixo foram comparadas exclusivamente na validação:

| Configuração | Mudança principal | Accuracy | Macro-F1 |
|---|---|---:|---:|
| Baseline majoritário | sempre prevê a classe mais frequente | 0,2846 | 0,0554 |
| TF-IDF unigrama | Logistic Regression sem pesos | 0,8537 | 0,8534 |
| Pesos balanceados | compensação integral do desbalanceamento | 0,8527 | 0,8558 |
| Unigramas e bigramas | contexto lexical adicional | 0,8479 | 0,8405 |
| Modelo selecionado | unigramas e pesos moderados | 0,8572 | 0,8617 |

O modelo final apresentou o melhor macro-F1 e a melhor acurácia de validação, mantendo um vocabulário muito menor que a alternativa com bigramas. Os experimentos completos estão em [`experiments/classification`](experiments/classification).

## Geração da justificativa

A justificativa oficial é determinística:

1. o texto é transformado em TF-IDF;
2. cada feature presente é multiplicada pelo coeficiente da classe prevista;
3. as maiores contribuições positivas e informativas são selecionadas;
4. essas evidências formam uma justificativa de uma a três frases.

A justificativa explica os sinais usados pelo classificador. Ela não solicita a um LLM que invente uma explicação depois da previsão.

Uma reescrita opcional com LLM foi testada, mas não demonstrou ganho qualitativo e introduziu falhas de disponibilidade, latência e dependência externa. Por isso, permanece apenas como experimento em [`docs/experiments/llm-justification.md`](docs/experiments/llm-justification.md).

## Baixa confiança

Previsões com confiança inferior a `0.60` são sinalizadas. O limiar foi escolhido somente na validação: sinalizou 25,71% dos tickets e capturou 70,54% dos erros.

O alerta modifica apenas a redação da justificativa. Ele nunca altera a classe prevista. A probabilidade não foi formalmente calibrada e não deve ser interpretada como garantia de acerto.

## Teste interativo

A interface Streamlit é uma camada fina sobre o mesmo serviço usado nos testes e na avaliação. Ela permite digitar um ticket, visualizar classe e justificativa, consultar confiança e evidências e inspecionar o JSON exigido. A interface não carrega datasets, calcula métricas ou acessa o teste final.

## Métricas finais

Depois do congelamento da configuração, o modelo foi retreinado com treino e validação e avaliado uma única vez nos 200 tickets finais.

| Métrica | Resultado |
|---|---:|
| Accuracy | 0,9050 |
| Macro-F1 | 0,9135 |
| Weighted-F1 | 0,9061 |
| Acertos | 181 |
| Erros | 19 |

Todas as oito classes tiveram F1 acima de `0.84`. `Miscellaneous` apresentou a menor precisão (`0.7714`), coerente com seu caráter residual e com o vocabulário compartilhado com outras classes.

O limiar de baixa confiança sinalizou 49 tickets e concentrou 16 dos 19 erros. A avaliação completa está em [`docs/reports/final-evaluation.md`](docs/reports/final-evaluation.md). Os resultados auditáveis ficam em `outputs/final/`.

## Principais trade-offs

- Unigramas foram melhores e muito menores que bigramas, mas capturam menos contexto de frases.
- Pesos moderados melhoraram o equilíbrio entre classes, aceitando mudanças pontuais de precisão e recall.
- A justificativa determinística é fiel, rápida e local, mas pode soar menos natural que uma redação generativa.
- A confiança ajuda na triagem, mas não possui calibração formal.
- A arquitetura prioriza clareza e reprodução local em vez de componentes distribuídos ou uma API de produção.

## Limitações

- o dataset aparenta já ter sido processado;
- entradas brutas reais podem diferir da distribuição de treinamento;
- quase duplicatas semânticas não foram auditadas;
- as probabilidades não foram formalmente calibradas;
- algumas classes compartilham vocabulário;
- tickets curtos ou ambíguos podem fornecer pouca evidência;
- a interface foi criada para demonstração local, não para produção.

## O que faria com mais tempo

- auditaria quase duplicatas semânticas antes da divisão;
- realizaria avaliação humana das justificativas;
- calibraria as probabilidades em uma partição dedicada;
- compararia TF-IDF com embeddings e ensembles usando um novo teste;
- adicionaria API, observabilidade e monitoramento de drift.

## Estrutura do projeto

```text
data/                    splits reproduzíveis
prep/                    criação e validação dos splits
src/ticket_classifier/
  classification/        vetorização, modelo e inferência
  flow/                  treinamento e entrega da previsão
  justification/         evidências e justificativas
  metrics/               confiança e avaliação final
interface/               aplicação Streamlit
experiments/             EDA e modelos testados no desenvolvimento
outputs/                 resultados oficiais
docs/                    decisões e relatórios detalhados
tests/                   testes automatizados
```

## Reprodutibilidade

A instalação, o treinamento, os testes e o Streamlit foram validados em ambiente virtual limpo e em Docker. O fluxo verifica hashes e contagens antes de carregar os splits. Os resultados finais não foram usados para alterar modelo, features, pesos, limiar ou justificativa.

As decisões arquiteturais completas permanecem em [`docs/decisions`](docs/decisions).
