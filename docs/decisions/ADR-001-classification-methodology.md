# ADR-001: Metodologia de classificação dos tickets

## Status

Aceita.

## Data

10 de setembro de 2026.

## Contexto

O desafio pede um fluxo que receba o texto de um chamado de TI e retorne uma classe e uma justificativa curta, com uma a três sentenças, explicando os termos ou padrões que sustentam a classificação.

A entrega deve incluir uma forma interativa de testar novos tickets, métricas calculadas sobre uma amostra de 200 tickets, código reproduzível, resultados salvos e uma explicação das escolhas e dos trade-offs. O prazo disponível para construir, validar, documentar e preparar a apresentação da solução é de 48 horas.

Por isso, a arquitetura precisa equilibrar:

- qualidade de classificação;
- fidelidade das justificativas;
- reprodutibilidade;
- simplicidade operacional;
- alinhamento com o contexto de IA generativa;
- capacidade de conclusão no prazo;
- facilidade de compreensão e defesa em uma entrevista técnica.

## Evidências da análise exploratória

Esta decisão se baseia nos relatórios produzidos na [análise exploratória](../reports/eda.md).

### Volume e supervisão

O dataset possui:

- 47.837 tickets;
- uma coluna de entrada, `Document`;
- uma coluna-alvo, `Topic_group`;
- oito classes;
- nenhum texto nulo ou vazio;
- nenhum rótulo nulo ou vazio.

Todas as classes possuem quantidade material de exemplos. A menor classe, `Administrative rights`, contém 1.760 registros. Isso favorece aprendizado supervisionado e reduz a necessidade de depender de um LLM para inferir a taxonomia somente a partir de instruções ou de poucos exemplos.

### Distribuição das classes

| Classe | Registros | Percentual |
| --- | ---: | ---: |
| Hardware | 13.617 | 28,47% |
| HR Support | 10.915 | 22,82% |
| Access | 7.125 | 14,89% |
| Miscellaneous | 7.060 | 14,76% |
| Storage | 2.777 | 5,81% |
| Purchase | 2.464 | 5,15% |
| Internal Project | 2.119 | 4,43% |
| Administrative rights | 1.760 | 3,68% |

A maior classe possui 7,74 vezes mais registros que a menor. Prever sempre `Hardware` já produziria 28,47% de acurácia, portanto a acurácia isolada não será suficiente para selecionar ou avaliar o modelo.

O desbalanceamento é relevante, mas a menor classe ainda possui exemplos suficientes. Não há evidência para descartar dados por undersampling ou replicar registros por oversampling como primeira medida.

### Comprimento e características do texto

O ticket mediano possui 26 palavras. O primeiro quartil possui 17 palavras e o terceiro, 46. A maioria dos textos é curta, condição em que palavras e pequenas expressões podem carregar sinais classificatórios importantes.

A distribuição possui uma cauda longa:

- P95 de 136 palavras;
- P99 de 284 palavras;
- máximo de 981 palavras.

Os exemplos mais longos contêm cadeias de e-mail, assinaturas, avisos legais e conteúdo repetido. Esse material pode introduzir ruído ou atalhos espúrios. Textos extremamente curtos também existem, mas são raros: 49 tickets possuem até três palavras, correspondendo a aproximadamente 0,10% do dataset.

Os comprimentos variam entre classes. `Hardware`, por exemplo, possui mediana de 32 palavras, enquanto `Storage` possui mediana de 21. O comprimento poderá funcionar como sinal indireto da classe e deverá ser observado durante a análise dos resultados.

### Pré-processamento anterior

Os textos aparecem predominantemente em minúsculas, com pouca pontuação e estrutura gramatical reduzida. Há sinais de que o dataset passou por processamento anterior, mas o procedimento original não foi identificado nem reproduzido.

Consequentemente, não será aplicado inicialmente outro processo agressivo de limpeza, como stemming, lematização, remoção de stopwords, remoção de números ou correção ortográfica. Essas transformações poderiam eliminar sinais ainda úteis sem que fosse possível recuperar o texto original.

### Duplicatas e conflitos

A auditoria não encontrou:

- pares com texto e rótulo exatamente iguais;
- textos brutos repetidos;
- textos repetidos após normalização conservadora de espaços;
- textos idênticos associados a rótulos conflitantes.

Esse resultado não elimina o risco de quase duplicatas, paráfrases ou cadeias de e-mail parcialmente compartilhadas. Esses casos não foram cobertos pela auditoria determinística e deverão ser considerados na estratégia de divisão dos dados.

## Alternativas consideradas

### Embeddings com classificador supervisionado

#### Funcionamento

Um modelo de embeddings transformaria cada ticket em um vetor semântico. Um classificador supervisionado seria treinado sobre esses vetores para aprender as oito classes.

#### Vantagens

- captura relações semânticas e sinônimos;
- depende menos de correspondência lexical exata;
- pode generalizar melhor para formulações novas;
- pode apoiar uma futura busca por tickets semelhantes.

#### Desvantagens

- exige a seleção, instalação e execução de um modelo adicional;
- aumenta o tempo e a complexidade operacional;
- oferece menor explicabilidade por palavra ou expressão;
- pode exigir download significativo ou uma API externa;
- um embedding genérico pode não representar corretamente a taxonomia interna;
- o texto já degradado pode reduzir a vantagem semântica esperada;
- não existe evidência, antes da modelagem, de que superará TF-IDF neste dataset.

#### Motivo da não escolha

O desafio exige justificativas concretas baseadas nos termos ou padrões que conduziram à classe. Embeddings tornam essa ligação menos direta principalmente levando em consideração o pré processamento feito que removeu parte da estrutura gramatical dos textos e pode afetar semântica dos mesmos. Dentro do prazo, o possível ganho semântico não compensa a complexidade e a perda de explicabilidade.

### Few-shot prompting com LLM

#### Funcionamento

Um LLM receberia a descrição da tarefa, as classes, alguns tickets já classificados e um novo ticket. O próprio LLM decidiria a classe e produziria a justificativa.

#### Vantagens

- boa compreensão de linguagem natural;
- capacidade de lidar com formulações semanticamente variadas;
- geração direta de justificativas naturais;
- não exige treinamento supervisionado convencional.

#### Desvantagens

- utiliza somente os poucos exemplos que cabem no prompt, apesar da existência de 47.837 tickets rotulados;
- exige selecionar exemplos representativos, criando uma nova decisão de modelagem;
- as classes não possuem definições formais completas fora dos próprios dados;
- o resultado pode variar entre execuções;
- prompts maiores aumentam custo e latência;
- exige credenciais, controle de limites, validação e tratamento de falhas;
- o LLM pode devolver uma classe válida por uma justificativa incorreta ou inventada;
- dificulta a reprodução exata das métricas sobre 200 tickets;
- o texto previamente processado pode prejudicar a compreensão linguística do LLM.

#### Motivo da não escolha

O dataset já oferece supervisão em escala suficiente para aprender a taxonomia diretamente. Usar poucos exemplos no prompt descartaria grande parte dessa informação e tornaria a classificação mais variável e cara. O LLM será usado somente em uma função restrita de redação da justificativa, sem autoridade para decidir a classe.

### RAG com recuperação de tickets semelhantes

#### Funcionamento

Os tickets históricos seriam indexados por embeddings. Para cada novo ticket, o sistema recuperaria exemplos semelhantes e os forneceria a um LLM para produzir a classificação e a justificativa.

#### Vantagens

- seleciona exemplos contextuais para cada entrada;
- permite apresentar tickets semelhantes como evidência adicional;
- aproveita o histórico sem incluir todos os registros no prompt;
- pode ajudar a interpretar categorias ambíguas.

#### Desvantagens

- exige embeddings, índice de busca, estratégia de recuperação e LLM;
- introduz mais componentes para implementar, testar e explicar;
- boilerplate e cadeias de e-mail podem dominar a similaridade;
- tickets semelhantes podem possuir rótulos diferentes;
- a recuperação pode causar vazamento se incluir registros de avaliação;
- similaridade não demonstra necessariamente por que determinada classe foi escolhida;
- o problema é de classificação supervisionada, não de recuperação de conhecimento externo.

#### Motivo da não escolha

RAG adicionaria complexidade sem resolver uma necessidade comprovada. As classes são fixas e existem milhares de exemplos rotulados para aprender diretamente a fronteira de decisão. Recuperação por similaridade poderá ser considerada no futuro como recurso de auditoria ou interface, mas nesse momento não será o núcleo da classificação.

## Decisão

A solução adotará uma arquitetura híbrida e controlada:

1. normalização textual mínima;
2. representação por TF-IDF de palavras, usando unigramas e bigramas;
3. classificação por Logistic Regression multiclasse com pesos balanceados;
4. extração das features com maior contribuição positiva para a classe prevista;
5. redação da justificativa por um LLM leve, usando somente a classe e as evidências fornecidas;
6. validação da justificativa;
7. fallback determinístico quando a geração estiver indisponível ou inválida;
8. retorno do JSON.

O classificador supervisionado será a única autoridade sobre a classe. O LLM não poderá alterar a previsão, recalcular a confiança ou introduzir evidências não fornecidas.

## Justificativa da decisão

### TF-IDF de palavras e bigramas

TF-IDF é adequado porque a maioria dos tickets é curta e as classes provavelmente apresentam vocabulário e expressões técnicas características. Unigramas capturam termos individuais, enquanto bigramas preservam expressões como `password reset`, `admin rights` e `disk space`.

A representação é rápida, local, reproduzível e permite relacionar diretamente a previsão aos termos do ticket.

N-gramas de caracteres não serão incluídos inicialmente. Embora possam ajudar com ruído e variações ortográficas, aumentam o espaço de features, podem aprender fragmentos de boilerplate e produzem evidências pouco legíveis para o usuário.

### Logistic Regression

Logistic Regression funciona bem sobre matrizes esparsas de texto e oferece:

- classificação multiclasse;
- coeficientes interpretáveis;
- probabilidades por classe;
- suporte a pesos balanceados;
- treinamento e inferência rápidos.

LinearSVC poderia apresentar desempenho competitivo, mas não fornece probabilidades nativas. Sua adoção exigiria abrir mão de uma medida de confiança ou adicionar calibração, aumentando o escopo. Logistic Regression oferece o melhor equilíbrio para a solução completa.

### Pesos balanceados

Os pesos balanceados reduzem o risco de o modelo favorecer excessivamente `Hardware` e `HR Support`. Essa decisão prioriza desempenho equilibrado entre classes e é coerente com o uso de macro-F1 como métrica principal.

O trade-off esperado é uma possível redução da precisão nas classes maiores ou da acurácia global. Esse efeito deverá ser observado na avaliação por classe e na matriz de confusão.

### Evidências determinísticas

Para cada ticket, serão calculadas as contribuições das features presentes para a classe prevista. Os termos ou bigramas com maior contribuição positiva formarão a base factual da justificativa.

Essa etapa separa explicação de redação: o classificador determina os sinais, enquanto o LLM apenas os transforma em uma frase natural.

### LLM restrito à redação

O LLM será utilizado para melhorar clareza e naturalidade, atendendo ao enquadramento de IA generativa sem tornar a classificação dependente de uma geração probabilística.

O LLM receberá somente informações controladas, como:

- classe prevista;
- termos ou padrões relevantes;
- trecho necessário do ticket.

A saída deverá possuir de uma a três sentenças, não poderá alterar a classe nem incluir fatos ausentes. Uma saída inválida ou uma falha do serviço acionará uma justificativa determinística.

### Fluxo explícito

O processo será organizado como um pequeno fluxo de estados com responsabilidades claras. O uso de um grafo somente se justifica porque existem rotas reais:

- entrada válida ou inválida;
- confiança regular ou baixa;
- serviço generativo disponível ou indisponível;
- justificativa válida ou inválida;
- resposta generativa ou fallback.

O fluxo não será um agente autônomo. Nenhum componente poderá escolher livremente ferramentas ou modificar a metodologia em tempo de execução.

## Fluxo conceitual

```text
Ticket
  |
  v
Validar e normalizar
  |
  v
TF-IDF + Logistic Regression
  |
  v
Classe, probabilidade e evidências
  |
  v
Gerar justificativa com LLM
  |
  +-- resposta válida --------> JSON final
  |
  +-- erro ou resposta inválida
                |
                v
      Justificativa determinística
                |
                v
             JSON final
```

## Trade-offs aceitos

### Capacidade lexical em vez de compreensão semântica profunda

TF-IDF depende de termos observados no treinamento e pode ter dificuldade com sinônimos inéditos. Essa limitação é aceita em troca de velocidade, transparência e aderência ao perfil curto e previamente processado dos textos.

### Equilíbrio entre classes em vez de máxima acurácia agregada

Os pesos balanceados podem reduzir a acurácia total ao aumentar a sensibilidade às classes menores. A decisão prioriza desempenho mais uniforme e deverá ser avaliada principalmente por macro-F1 e métricas por classe.

### Probabilidades úteis, mas não necessariamente calibradas

As probabilidades da Logistic Regression serão tratadas como pontuações de confiança do modelo, não como garantias estatísticas de acerto. A calibração formal fica fora do escopo inicial.

### Redação natural com dependência opcional

O LLM melhora a experiência do usuário, mas introduz latência, custo, credenciais e possibilidade de falha. O fallback determinístico impede que essa dependência interrompa o funcionamento principal.

### Fluxo explícito com abstração adicional

O grafo de estados melhora a visibilidade das decisões e dos fallbacks, mas adiciona uma dependência e uma camada conceitual. Ele será mantido pequeno e limitado às transições necessárias.

### Preservação dos dados com risco de ruído

Tickets muito curtos e longos não serão removidos inicialmente. Isso evita melhorar artificialmente as métricas ou apagar conteúdo relevante, mas preserva ruído e boilerplate que podem influenciar o modelo.

## Riscos e controles

| Risco | Controle planejado |
| --- | --- |
| Favorecimento das classes maiores | Pesos balanceados e avaliação por classe |
| Métrica inflada por quase duplicatas | Auditoria adicional e agrupamento antes do split, quando aplicável |
| Boilerplate como atalho | Inspeção das features globais e dos erros mais confiantes |
| Diferença entre texto processado e entrada bruta | Normalização consistente e documentação da limitação |
| Ticket sem evidência suficiente | Sinalização de baixa confiança e justificativa cautelosa |
| LLM inventar evidências | Entrada restrita, validação e fallback determinístico |
| API generativa indisponível | Execução funcional sem o LLM |
| Probabilidade interpretada como garantia | Rotulagem explícita como confiança estimada |

## Consequências para as próximas etapas

Esta decisão determina que:

- o split deverá ser estratificado e reservar exatamente 200 tickets para avaliação final;
- quase duplicatas deverão ser investigadas antes de congelar o split;
- a seleção e a avaliação deverão priorizar macro-F1, sem omitir acurácia e métricas por classe;
- a matriz de confusão será necessária para identificar fronteiras problemáticas;
- as contribuições locais das features deverão ser preservadas para a explicação;
- a interface deverá funcionar mesmo sem acesso ao serviço generativo;
- o resultado salvo deverá distinguir a classe, a confiança, as evidências e a origem da justificativa;
- o README deverá resumir esta decisão e apontar para este ADR.

## Critérios de sucesso

A metodologia será considerada adequada se:

- superar de forma clara o baseline majoritário de 28,47%;
- apresentar macro-F1 coerente com a acurácia;
- não abandonar as classes minoritárias;
- produzir justificativas relacionadas ao conteúdo real dos tickets;
- concluir a avaliação de 200 tickets de forma reproduzível;
- permanecer funcional quando o LLM estiver indisponível;
- permitir explicar os erros e os trade-offs observados.

## Critérios para reconsiderar a decisão

A arquitetura deverá ser reavaliada se os resultados demonstrarem uma ou mais destas condições:

- desempenho lexical insuficiente mesmo em tickets informativos;
- erros frequentes causados por sinônimos ou formulações semanticamente equivalentes;
- confusão persistente entre classes que não possa ser explicada por ruído de rótulo;
- evidências extraídas dominadas por assinaturas, avisos legais ou outros atalhos;
- pesos balanceados causando degradação desproporcional nas classes maiores;
- diferença material entre entradas brutas da interface e textos processados do dataset;
- justificativas generativas acrescentando informações não sustentadas pelas evidências.

Nesses casos, embeddings supervisionados poderão ser reconsiderados para a classificação, e recuperação por similaridade poderá ser avaliada como recurso auxiliar. RAG ou few-shot prompting somente serão reconsiderados se surgir uma necessidade concreta que o classificador supervisionado não consiga atender.

## Limitações desta decisão

Esta decisão registra a arquitetura com melhor adequação conhecida antes da modelagem. Ela não afirma que TF-IDF e Logistic Regression constituem o melhor modelo possível em termos absolutos.

A adequação deverá ser confirmada pela implementação, pelas métricas sobre a amostra isolada de 200 tickets e pela análise qualitativa dos erros e das justificativas.
