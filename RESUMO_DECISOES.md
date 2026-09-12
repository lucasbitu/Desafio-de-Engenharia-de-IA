# Resumo de decisões — QuantumRise Ticket Classifier

## Cinco decisões arquiteturais

1. **Aprendizado supervisionado clássico em vez de LLM, RAG ou embeddings.** O problema tem 47.837 exemplos rotulados e apenas oito classes fixas, portanto a supervisão disponível já é suficiente para construir um classificador local, rápido e rastreável. **Trade-off:** abre mão da possível generalização semântica de embeddings e LLMs em troca de menor custo, latência, variabilidade e exposição de dados.

2. **Logistic Regression como classificador.** O modelo funciona bem com texto esparso representado por TF-IDF, treina rapidamente e permite relacionar cada previsão diretamente aos pesos das palavras. **Trade-off:** oferece menos capacidade para capturar relações linguísticas complexas que modelos não lineares ou neurais.

3. **TF-IDF com unigramas, sem bigramas no modelo final.** Na validação, os unigramas produziram resultados melhores e um vocabulário muito menor; adicionar bigramas reduziu a accuracy para 0,8479 e o macro-F1 para 0,8405. **Trade-off:** o modelo fica mais simples e eficiente, mas entende menos contexto formado por sequências de palavras.

4. **Pesos moderados por classe para tratar o desbalanceamento.** Os pesos proporcionais à raiz quadrada do desbalanceamento reduziram a dominância das classes frequentes e produziram o melhor resultado de validação: accuracy 0,8572 e macro-F1 0,8617. **Trade-off:** melhora o equilíbrio global entre classes, aceitando alterações pontuais de precisão e recall; pesos totalmente balanceados foram considerados agressivos demais.

5. **Justificativa determinística; LLM opcional e desativado no fluxo oficial.** A explicação usa as maiores contribuições positivas de TF-IDF multiplicadas pelos coeficientes da classe prevista, mantendo a justificativa ligada aos sinais reais do modelo. **Trade-off:** a redação pode soar menos natural, mas é rápida, local, reproduzível e não depende de credenciais; a reescrita com LLM não demonstrou ganho qualitativo que compensasse latência, custo e risco de indisponibilidade.

## Pontos fracos conhecidos

- O dataset aparenta ter sido previamente processado; tickets reais brutos podem ter outra distribuição.
- Quase duplicatas semânticas não foram auditadas antes da divisão.
- As probabilidades não possuem calibração formal; confiança abaixo de 0,60 é um sinal de triagem, não garantia de erro.
- Algumas classes compartilham vocabulário; `Miscellaneous` é especialmente residual e teve a menor precisão final, 0,7714.
- Tickets curtos ou ambíguos podem produzir pouca evidência para a classificação e a justificativa.
- Unigramas não capturam todo o contexto de frases, e a justificativa determinística pode ser menos natural.
- O Streamlit é uma demonstração local, não uma interface de produção.

## Com mais tempo

- Auditar quase duplicatas semânticas antes da divisão.
- Avaliar as justificativas com pessoas.
- Calibrar probabilidades em uma partição dedicada.
- Comparar TF-IDF, embeddings e ensembles usando um novo teste.
- Adicionar API, observabilidade e monitoramento de drift.

**Números para memorizar:** teste final com 200 tickets; 181 acertos e 19 erros; accuracy 0,9050; macro-F1 0,9135; weighted-F1 0,9061; 16 dos 19 erros concentrados entre os 49 tickets sinalizados como baixa confiança.