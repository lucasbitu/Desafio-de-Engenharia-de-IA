# ADR-005: Interface Streamlit como camada fina de apresentação

## Status

Aceita.

## Data

11 de setembro de 2026.

## Contexto

O ADR-004 consolidou o E04 como baseline de desenvolvimento e determinou que o próximo marco seria disponibilizar uma interface interativa antes da criação do release candidate e da avaliação final dos 200 tickets.

Antes desta decisão, o projeto já possuía análise exploratória reproduzível, divisão congelada, modelo selecionado, pipeline reutilizável, contrato público, justificativa determinística, política de baixa confiança, treinamento reproduzível e 33 testes automatizados aprovados.

O desafio exige uma forma simples e interativa de inserir um ticket novo e receber sua classe e justificativa. A interface precisa cumprir esse requisito sem criar uma segunda implementação da lógica já validada no backend.

## Força arquitetural

A principal restrição é preservar uma única autoridade para classificação e entrega:

```text
Interface
  -> DeliveryPredictionService
       -> TicketClassifier
       -> política de baixa confiança
       -> justificativa determinística
  -> resposta pública
```

A interface não pode conhecer ou reproduzir configuração do TF-IDF, pesos da Logistic Regression, cálculo da classe ou confiança, limiar, seleção de evidências, justificativa, preparação ou divisão dos dados.

## Alternativas consideradas

### Interface de linha de comando

Uma CLI atenderia ao requisito mínimo com poucas dependências, mas foi rejeitada como interface principal por oferecer menor clareza visual para demonstrar classe, justificativa, JSON e diagnóstico opcional simultaneamente.

### API com FastAPI

Uma API ofereceria contrato HTTP e integração externa, mas exigiria uma ferramenta adicional para interação humana. O desafio pede um teste interativo leve, não uma integração de produção completa.

### Interface com lógica própria de inferência

Carregar o pipeline e reproduzir cálculos na interface foi rejeitado porque duplicaria responsabilidades, permitiria divergências e enfraqueceria os testes do `DeliveryPredictionService`.

### Streamlit como camada fina

Streamlit permite uma aplicação local leve com pouco código de apresentação, mantendo todo o comportamento no backend. Essa alternativa foi escolhida pelo equilíbrio entre simplicidade, clareza e capacidade de demonstração.

## Decisão

Adotar uma aplicação Streamlit no arquivo `interface/app.py`.

A aplicação deverá:

1. carregar `outputs/development/model.joblib`;
2. construir o serviço por `DeliveryPredictionService.from_model_path`;
3. coletar o texto do ticket;
4. tratar entrada vazia antes da inferência;
5. executar a previsão por `DeliveryPredictionService.predict`;
6. exibir `class` e `justification`;
7. apresentar o JSON público com exatamente esses campos;
8. permitir diagnósticos opcionais por `DeliveryPredictionService.diagnose`;
9. comunicar ausência ou falha de carregamento do modelo;
10. tratar falhas de validação ou inferência sem expor detalhes internos.

O diagnóstico opcional pode exibir confiança estimada, indicação de baixa confiança e recomendação de revisão humana. Esses dados não fazem parte do JSON obrigatório e não podem alterar a resposta pública.

## Dependência

Streamlit será tratado como dependência opcional da apresentação e está centralizado no extra `interface` de `pyproject.toml`.

```powershell
.venv\Scripts\python -m pip install -e ".[interface]"
.venv\Scripts\python -m streamlit run interface/app.py
```

Como o modelo não é versionado, uma instalação limpa deve executar `ticket-train` antes de iniciar a interface.

## Contrato preservado

```json
{
  "class": "...",
  "justification": "..."
}
```

A interface apenas serializa o `PredictionOutput` produzido pelo serviço. Confiança, evidências e baixa confiança permanecem diagnósticos internos.

## Proteção do teste final

A interface está proibida de importar `test.csv`, conhecer o caminho da partição final, ler CSVs, importar scripts de divisão, calcular métricas, retreinar o modelo, selecionar limiares ou ajustar parâmetros a partir de entradas interativas.

Uma verificação automatizada recusa referências associadas ao acesso direto aos dados ou ao teste final. Os 200 tickets continuam selados.

## Validação automatizada

A implementação adicionou cinco testes que cobrem:

- equivalência entre a saída visual e `DeliveryPredictionService.predict`;
- JSON restrito a `class` e `justification`;
- tratamento de entrada vazia;
- mensagem acionável quando o modelo está ausente;
- diagnóstico de baixa confiança sem alteração da classe;
- ausência de acesso ao dataset e ao teste final.

Contrato e equivalência são cobertos pelo mesmo caso. A suíte passou de 33 para 38 testes, todos aprovados.

## Consequências positivas

- o requisito de teste interativo passa a ser atendido;
- backend e interface compartilham a mesma autoridade;
- nenhuma regra de ML é duplicada;
- o contrato público permanece explícito;
- diagnósticos enriquecem a demonstração sem contaminar o JSON;
- falhas comuns possuem mensagens compreensíveis;
- a proteção do teste final permanece ativa.

## Consequências negativas e custos aceitos

- Streamlit adiciona dependências transitivas;
- a interface é voltada à demonstração local, não a uma API de produção;
- o artefato de desenvolvimento precisa existir antes da inicialização;
- diagnósticos opcionais causam uma segunda inferência sobre o mesmo texto;
- os testes integrados dependem da reprodução prévia do modelo de desenvolvimento;
- confiança continua sendo uma estimativa não calibrada.

## Limitações conhecidas

- entradas brutas podem diferir dos textos processados do dataset;
- tickets curtos ou ambíguos podem ter baixa confiança;
- a aplicação ainda não foi validada em instalação totalmente limpa;
- o README principal ainda precisa incorporar as instruções da interface;
- o executor isolado da avaliação final ainda não existe.

## Gates satisfeitos

Esta decisão satisfaz os seguintes itens do ADR-004:

- existe uma interface interativa;
- ela reutiliza o serviço já testado;
- a resposta pública mantém o contrato;
- baixa confiança não altera a classe;
- a camada visual não acessa o teste final;
- os 38 testes estão aprovados.

## Próxima prioridade

O próximo gate é reproduzir o projeto em ambiente limpo:

1. criar novo ambiente virtual;
2. instalar somente as dependências declaradas;
3. instalar a dependência da interface;
4. reproduzir o modelo de desenvolvimento;
5. confirmar hashes, métricas e metadados;
6. executar os 38 testes;
7. iniciar o Streamlit;
8. realizar um smoke test;
9. confirmar que nenhum fluxo comum acessa `test.csv`.

O teste final permanecerá fechado durante toda essa etapa.

## Critérios para reconsideração

Esta decisão poderá ser revista se a avaliação exigir integração HTTP, se Streamlit for incompatível com o ambiente de entrega ou se surgirem requisitos de autenticação, concorrência ou produção.

Qualquer substituição deverá preservar `DeliveryPredictionService` como fronteira do backend ou registrar explicitamente uma nova decisão arquitetural.

