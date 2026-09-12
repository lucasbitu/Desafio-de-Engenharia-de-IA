# ADR-009 — Reescrita generativa opcional sem framework de grafo

- Status: aceito
- Data: 2026-09-12
- Contexto temporal: decisão posterior à avaliação final

## Contexto

A baseline utiliza uma justificativa determinística fiel às contribuições locais do E04.
Havia interesse em acrescentar IA generativa onde ela agrega valor — qualidade da redação —
sem transferir ao LLM autoridade sobre a classificação.

O fluxo possui uma única bifurcação operacional: aceitar uma reescrita válida ou usar o
fallback determinístico. Um framework de grafo adicionaria dependência, superfície de falha e
complexidade conceitual sem oferecer benefício proporcional.

## Decisão

Implementar uma porta `JustificationRewriter` opcional dentro do serviço de entrega, com
adaptadores para Gemini e OpenAI. O provedor é selecionado por configuração e a orquestração
continuará explícita em Python comum, sem agente e sem LangGraph.

O fluxo é:

```text
ticket -> classificador congelado -> classe/confiança/evidências
       -> fallback determinístico
       -> LLM opcional somente para redação
            -> validação aprovada -> texto generativo
            -> erro/timeout/saída inválida -> fallback determinístico
       -> contrato público imutável {class, justification}
```

## Guardrails

- a classe é calculada antes da chamada generativa e nunca pode ser alterada;
- o prompt recebe apenas dados estruturados e evidências locais permitidas;
- a resposta deve conter a classe exata e pelo menos uma evidência fornecida;
- são permitidas de uma a três sentenças e no máximo 600 caracteres;
- baixa confiança exige indicação de possível revisão humana;
- chamadas OpenAI solicitam que a resposta não seja armazenada (`store=false`);
- timeout, indisponibilidade, credencial ausente ou violação do contrato acionam o fallback;
- o contrato público permanece formado somente por `class` e `justification`.

## Configuração

A funcionalidade vem desativada. Sua ativação exige `ENABLE_LLM_JUSTIFICATION=true`. O
provedor padrão é `gemini`, configurado por `GEMINI_API_KEY` e, opcionalmente,
`GEMINI_MODEL`; o modelo padrão é `gemini-2.5-flash-lite`. `LLM_PROVIDER=openai` seleciona
o adaptador anterior e suas variáveis `OPENAI_*`.

O nível gratuito do Gemini é adequado somente à demonstração com entradas não sensíveis.
Pelos termos vigentes, conteúdo e respostas dessa modalidade podem ser usados para melhorar
produtos Google e passar por revisão humana. Tickets confidenciais, pessoais ou de produção
não devem ser enviados por essa rota.

## Consequências

A solução demonstra uso pontual de IA generativa sem comprometer a previsibilidade da
classificação. O custo e a latência só existem quando a opção está ativada. A validação é uma
barreira adicional, não uma prova semântica completa contra alucinação; por isso o LLM nunca
recebe autoridade sobre decisões.

Esta mudança ocorreu depois da avaliação final. Ela foi testada com doubles locais e não
reabriu nem utilizou o conjunto final de 200 tickets. As métricas finais continuam atribuídas
ao release candidate congelado, não à qualidade textual desta camada posterior.
