# ADR-004 — Baseline de desenvolvimento, governança e gates de entrega

- **Status:** Aceito
- **Data:** 11 de setembro de 2026
- **Escopo:** estado consolidado do classificador de tickets antes da interface interativa e da avaliação final
- **Decisões relacionadas:** [ADR-001](ADR-001-classification-methodology.md), [ADR-002](ADR-002-final-model-selection.md) e [ADR-003](ADR-003-low-confidence-policy.md)

## Contexto

O projeto já ultrapassou a fase de exploração e seleção experimental. Há uma divisão de dados congelada, um modelo escolhido, um contrato de inferência, uma justificativa determinística, uma política de baixa confiança e um fluxo reproduzível de treinamento e validação.

Neste ponto, o principal risco não é a ausência de novas alternativas de modelagem. O risco é perder a coerência entre as decisões já tomadas, a implementação, os artefatos produzidos e o protocolo de avaliação final. Este ADR estabelece uma fonte consolidada de verdade para o restante da entrega.

Ele não substitui o histórico técnico dos ADRs anteriores. Seu papel é registrar a precedência entre eles, fixar a baseline atualmente verificada e definir as condições que devem ser satisfeitas antes de acessar os 200 tickets reservados para teste final.

## Decisão

Adotamos como baseline oficial de desenvolvimento:

1. o experimento **E04**, composto por TF-IDF de unigramas e Regressão Logística com pesos moderados;
2. o contrato público de resposta formado exclusivamente por `class` e `justification`;
3. explicações produzidas de forma determinística a partir das contribuições positivas do próprio modelo;
4. limiar de baixa confiança igual a **0,60**, usado para sinalização e cautela operacional, sem alterar a classe prevista;
5. treinamento e avaliação de desenvolvimento restritos às partições de treino e validação;
6. os 200 tickets de teste final permanecem selados até que todos os gates de entrega definidos neste documento sejam satisfeitos.

## Precedência das decisões

Em caso de aparente conflito, vale a seguinte ordem:

1. este ADR define a baseline integrada e os gates de entrega;
2. o ADR-003 rege a política de baixa confiança e a forma da justificativa;
3. o ADR-002 rege a escolha final do modelo;
4. o ADR-001 permanece como registro da metodologia e das hipóteses iniciais.

Consequentemente:

- a escolha de unigramas e pesos moderados do ADR-002 substitui a hipótese inicial de bigramas e `class_weight="balanced"` do ADR-001;
- geração de justificativa por LLM, mencionada como possibilidade no ADR-001, não faz parte da solução aceita nesta baseline;
- não há necessidade atual de agentes, grafos ou frameworks de orquestração: o pipeline explícito e determinístico atende ao contrato com menor complexidade e maior auditabilidade.

## Estado atual verificado

### Dados e isolamento do teste

- Dataset consolidado: **47.837** registros.
- Treino: **38.109** registros.
- Validação: **9.528** registros.
- Teste final reservado: **200** registros.
- Semente usada na divisão e no modelo: **42**.
- O teste final não foi acessado pelo fluxo implementado em `src/` nem pelos testes automatizados.

Hashes SHA-256 registrados para rastreabilidade:

| Item | SHA-256 |
|---|---|
| Dataset consolidado | `044FDACE33FA564E1E60453F2941DAFC95539C99878B0D32746950394B9DD4D4` |
| Treino congelado | `62DA11CE58FA9EAF6C3AC04A77BE24FC0C66A97864829D68CA98FDBE6FDDF894` |
| Validação congelada | `4EEA86B63A3E3D7186C6F52C3FFF41D6D8E266679D7B9496428E3E2971366DB0` |
| Teste final congelado | `E857B8873DE34B47EC39360F82BD25A04497A811D9D985E835F9D1EEF27F5B6D` |

Os hashes são parte do protocolo. Uma divergência deve interromper a execução até que sua causa seja entendida; nunca deve ser corrigida silenciosamente por meio de uma nova divisão.

### Modelo canônico

O modelo aceito é o experimento `E04_tfidf_unigram_logreg_moderate_weights`, com os seguintes invariantes:

- TF-IDF por palavras;
- texto convertido para minúsculas;
- `ngram_range=(1, 1)`;
- `min_df=2`;
- normalização L2;
- `sublinear_tf=True`;
- matriz em `float64`;
- Regressão Logística com `C=1`, solver `lbfgs`, `max_iter=1000` e semente 42;
- pesos de classe moderados, calculados pela raiz quadrada do balanceamento inverso e normalizados;
- vocabulário observado na execução de referência: **8.544** termos.

Pesos registrados na execução de referência:

| Classe | Peso |
|---|---:|
| Access | 0,977253 |
| Administrative rights | 1,966320 |
| HR Support | 0,789575 |
| Hardware | 0,706892 |
| Internal Project | 1,792016 |
| Miscellaneous | 0,981673 |
| Purchase | 1,661759 |
| Storage | 1,565437 |

O artefato de modelo dessa execução tem SHA-256 `323E60EF470FBA8CF380A89399FC96C70A301088E6F5E0A0460D5D24247179DA`. A serialização e a recarga preservaram integralmente as previsões da validação.

### Desempenho de validação

Resultados da execução oficial de desenvolvimento:

| Métrica | Resultado |
|---|---:|
| Accuracy | 0,857158 |
| Macro F1 | 0,861702 |
| Weighted F1 | 0,857648 |

Resultados por classe:

| Classe | Precision | Recall | F1 | Suporte |
|---|---:|---:|---:|---:|
| Access | 0,911458 | 0,863284 | 0,886717 | 1.419 |
| Administrative rights | 0,791429 | 0,789174 | 0,790300 | 351 |
| HR Support | 0,873508 | 0,841766 | 0,857344 | 2.174 |
| Hardware | 0,824895 | 0,865044 | 0,844492 | 2.712 |
| Internal Project | 0,884337 | 0,869668 | 0,876941 | 422 |
| Miscellaneous | 0,805333 | 0,859175 | 0,831383 | 1.406 |
| Purchase | 0,936681 | 0,873727 | 0,904110 | 491 |
| Storage | 0,929119 | 0,877034 | 0,902326 | 553 |

Macro F1 permanece a métrica principal porque dá peso equivalente às oito classes e reduz o risco de esconder falhas nas classes minoritárias. Accuracy e Weighted F1 permanecem como métricas complementares.

### Política de baixa confiança

O limiar aceito é `0,60`, aplicado sobre a maior probabilidade prevista pela Regressão Logística.

Na validação:

- **2.450 de 9.528** previsões, ou **25,71%**, foram sinalizadas como baixa confiança;
- esse grupo concentrou **960 de 1.361** erros, ou **70,54%** dos erros observados;
- a accuracy abaixo do limiar foi **60,82%**;
- a accuracy a partir do limiar foi **94,33%**.

Portanto, a sinalização é operacionalmente informativa. Ela não funciona como rejeição automática e não altera a classe prevista. Seu objetivo é permitir uma mensagem mais cautelosa, revisão humana ou tratamento diferenciado pela camada consumidora.

### Contratos de inferência e entrega

O serviço interno retorna informações diagnósticas necessárias para auditoria:

- classe prevista;
- confiança;
- indicação de baixa confiança;
- evidências textuais extraídas do modelo.

O contrato público continua estrito:

```json
{
  "class": "nome exato da classe",
  "justification": "uma frase curta e determinística"
}
```

A justificativa:

- usa no máximo três evidências positivas presentes no ticket e relevantes para a classe prevista;
- é determinística para a mesma entrada e o mesmo artefato;
- não inventa termos quando não há evidência positiva utilizável;
- adota linguagem cautelosa quando a previsão está abaixo do limiar;
- não expõe confiança, vetores, coeficientes ou outros campos internos no contrato público.

### Reprodutibilidade e qualidade

O fluxo oficial de desenvolvimento:

- carrega somente treino e validação;
- valida os hashes de entrada;
- treina a fábrica canônica do E04;
- produz modelo, metadados, métricas e previsões de validação;
- impede sobrescrita acidental dos artefatos por padrão;
- verifica o round trip do modelo serializado;
- registra versões do ambiente.

Ambiente da execução de referência:

- Python 3.13.14;
- Windows 11;
- NumPy 2.4.3;
- pandas 2.3.3;
- Pydantic 2.11.7;
- scikit-learn 1.8.0;
- joblib 1.5.3.

A baseline foi verificada com **33 testes automatizados aprovados**, além da compilação dos módulos. Esses testes cobrem os contratos, a inferência, a justificativa, a baixa confiança e o fluxo de treinamento.

## Estrutura técnica consolidada

As responsabilidades permanecem separadas:

- `src/ticket_classifier/classification/model.py`: única fábrica autorizada do E04;
- `src/ticket_classifier/schemas.py`: validação das entradas e dos contratos;
- `src/ticket_classifier/classification/inference.py`: carregamento do artefato, predição, confiança e evidências;
- `src/ticket_classifier/justification/deterministic.py`: geração determinística das justificativas;
- `src/ticket_classifier/metrics/confidence.py`: política e avaliação do limiar;
- `src/ticket_classifier/flow/delivery.py`: composição do resultado interno e da resposta pública;
- `src/ticket_classifier/flow/prediction.py`: alias de compatibilidade da API anterior;
- `src/ticket_classifier/flow/training.py`: treinamento reproduzível e geração de artefatos de desenvolvimento.

Essa divisão evita que a futura interface contenha regras de negócio ou replique o pipeline. A interface deve apenas coletar a entrada, chamar o serviço de entrega e apresentar o resultado.

## Estado do repositório no momento deste ADR

O último commit consolidado identificado é `5375ce6` (`feat: adiciona inferência explicável e política de baixa confiança`). Sobre ele existe um bloco local já validado, porém ainda não consolidado em commit, que inclui:

- comando de treinamento reproduzível;
- empacotamento e dependências do projeto;
- README raiz;
- consolidação da API pública;
- testes do treinamento;
- artefatos de desenvolvimento protegidos contra versionamento indevido.

Este detalhe é importante: “validado localmente” e “registrado no histórico Git” não são equivalentes. A baseline só estará plenamente rastreável depois que essas mudanças e este ADR forem revisados e commitados.

## O que está concluído

- EDA e entendimento inicial do problema;
- congelamento determinístico das três partições;
- comparação experimental e escolha do E04;
- fábrica única do modelo escolhido;
- inferência por artefato serializado;
- contrato interno e contrato público;
- justificativa determinística baseada no modelo;
- política de baixa confiança e evidência quantitativa para o limiar;
- fluxo reproduzível de treino e validação;
- metadados, métricas, previsões e hashes de desenvolvimento;
- suíte automatizada para o núcleo já implementado.

## O que permanece pendente

- revisar e consolidar em commit o bloco local atual;
- implementar a interface interativa como camada fina sobre o serviço existente;
- completar o README com instruções da interface e com o procedimento final reproduzível;
- testar a interface e os fluxos de erro relevantes;
- realizar uma revisão final de segredos, dados e artefatos versionados;
- criar uma baseline de release identificada por commit;
- somente então treinar o artefato final e executar uma única avaliação nos 200 tickets selados;
- registrar e comunicar os resultados finais sem retroalimentá-los no modelo.

## Gates obrigatórios antes do teste final

O teste final só pode ser aberto quando todos os itens abaixo forem verdadeiros:

1. a interface interativa utiliza o mesmo serviço e o mesmo contrato cobertos pelos testes;
2. os testes automatizados passam no ambiente documentado;
3. o treinamento de desenvolvimento pode ser reproduzido a partir de um ambiente limpo;
4. README, ADRs e comandos de execução correspondem à implementação real;
5. não existem referências ao arquivo de teste final no código comum de treino, validação, interface ou testes automatizados;
6. os hashes das partições congeladas conferem;
7. parâmetros, features, classes, limiar e política de justificativa estão congelados;
8. há um commit de release identificável, sem mudanças locais não auditadas;
9. existe um avaliador final separado, de uso explícito e único, que não participa de seleção de modelo;
10. está definido onde serão registrados o hash do modelo final, as métricas finais e a confirmação de acesso único ao teste.

Após os gates, o modelo final deve ser treinado com **treino + validação**, preservando a fábrica e os hiperparâmetros congelados. Pesos dependentes da distribuição dos dados devem ser recalculados pelo mesmo algoritmo sobre esse conjunto combinado; não se deve copiar os valores numéricos da execução apenas com treino.

Os resultados dos 200 tickets são exclusivamente uma estimativa final de generalização. Eles não autorizam ajuste posterior de features, pesos, limiar, classes ou hiperparâmetros. Qualquer mudança após a abertura do teste invalida a interpretação daquele resultado como teste final independente.

## Riscos e limitações conhecidos

1. **Probabilidade não calibrada:** a maior probabilidade da Regressão Logística é útil como sinal relativo, mas não foi calibrada como probabilidade operacional absoluta.
2. **Sobreposição semântica:** classes como `Miscellaneous`, `Hardware`, `Access` e `Administrative rights` podem compartilhar vocabulário e contexto, mantendo erros estruturalmente ambíguos.
3. **Classes menores:** métricas de classes com menor suporte têm maior incerteza e devem ser interpretadas junto da matriz de confusão e de exemplos de erro.
4. **Explicação local limitada:** contribuição TF-IDF vezes coeficiente explica quais termos favoreceram a classe dentro do modelo linear; não demonstra causalidade nem captura toda a semântica do ticket.
5. **Entradas fora de distribuição:** textos vazios são rejeitados, mas linguagem inédita, muito curta ou com vocabulário ausente pode produzir justificativa genérica e baixa confiança.
6. **Duplicatas e contaminação semântica:** o congelamento protege a partição, mas não substitui uma auditoria explícita de duplicatas exatas ou quase duplicatas entre conjuntos, caso isso ainda não esteja evidenciado nos relatórios.
7. **Compatibilidade do artefato:** modelos serializados por joblib dependem do ambiente Python e das bibliotecas; por isso versões e hashes devem acompanhar o artefato.
8. **Ausência deliberada de LLM:** a solução não gera explicações livres mais sofisticadas. Em contrapartida, reduz custo, latência, variabilidade, risco de alucinação e dependência externa.

## Consequências

### Positivas

- uma única especificação conecta decisões, implementação, evidências e entrega;
- o teste final fica protegido contra uso iterativo e vazamento decisório;
- interface e futuros consumidores reutilizam o mesmo núcleo testado;
- resultados e artefatos tornam-se rastreáveis por hashes, versões e commits;
- justificativas são reproduzíveis e fiéis ao mecanismo do classificador.

### Negativas e custos aceitos

- o modelo linear pode ter teto de desempenho inferior ao de abordagens mais complexas;
- a política de baixa confiança adiciona um ramo de comunicação e testes;
- a disciplina de gates impede ajustes oportunistas depois de observar o teste;
- a execução final exige um fluxo separado e auditável.

## Critérios para reconsiderar esta decisão

Esta baseline só deve ser reaberta antes do teste final se ocorrer ao menos uma das condições abaixo:

- erro comprovado na divisão, nos hashes ou nos rótulos;
- falha de reprodução das métricas dentro de tolerância previamente definida;
- incompatibilidade entre o contrato exigido pelo desafio e o contrato implementado;
- defeito funcional que afete a classe, a justificativa ou a segurança do fluxo;
- evidência de vazamento de dados;
- alteração formal dos requisitos do desafio.

Uma reabertura deve gerar novo ADR ou alterar explicitamente o status dos ADRs afetados. Melhoria meramente especulativa de métrica não é justificativa suficiente para tocar o teste final.

## Evidências e fontes internas

- `docs/decisions/ADR-001-classification-methodology.md`
- `docs/decisions/ADR-002-final-model-selection.md`
- `docs/decisions/ADR-003-low-confidence-policy.md`
- `src/ticket_classifier/`
- `tests/`
- `outputs/development/run_metadata.json`
- `outputs/development/validation_metrics.json`
- `outputs/development/validation_predictions.csv`

## Resultado

O núcleo de classificação está tecnicamente consolidado para avançar à interface interativa. O próximo marco não é experimentar outro modelo, mas transformar essa baseline validada em uma release rastreável, completar a camada de interação e cumprir integralmente os gates antes do acesso único ao teste final.
