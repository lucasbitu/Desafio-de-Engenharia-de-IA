# Relatório consolidado da análise exploratória

## Objetivo e escopo

Este documento consolida a análise exploratória do dataset de chamados de TI: fonte e esquema, distribuição das classes, comprimento dos textos e duplicatas determinísticas. Nenhuma linha foi removida, nenhum texto foi transformado e nenhuma decisão de pré-processamento ou modelagem foi tomada.

## Dataset analisado

- Arquivo: all_tickets_processed_improved_v3.csv
- SHA-256: 044FDACE33FA564E1E60453F2941DAFC95539C99878B0D32746950394B9DD4D4
- Tamanho: 14.568.920 bytes
- Codificação: UTF-8
- Registros: 47.837
- Colunas: Document e Topic_group
- Textos nulos ou vazios: 0
- Rótulos nulos ou vazios: 0
- Classes: 8

O hash registra exatamente a versão utilizada e permite verificar a reprodutibilidade dos resultados.

## Distribuição da variável-alvo

| Classe | Quantidade | Percentual |
| --- | ---: | ---: |
| Hardware | 13.617 | 28,47% |
| HR Support | 10.915 | 22,82% |
| Access | 7.125 | 14,89% |
| Miscellaneous | 7.060 | 14,76% |
| Storage | 2.777 | 5,81% |
| Purchase | 2.464 | 5,15% |
| Internal Project | 2.119 | 4,43% |
| Administrative rights | 1.760 | 3,68% |

A maior classe possui 7,74 vezes mais registros que a menor. A classe majoritária representa 28,47% do dataset. Isso comprova desbalanceamento relativo, mas não determina qualquer técnica de correção.

## Perfil dos textos

| Métrica | Caracteres | Palavras |
| --- | ---: | ---: |
| Mínimo | 7 | 2 |
| P25 | 110 | 17 |
| Mediana | 175 | 26 |
| Média | 291,87 | 43,60 |
| P75 | 304 | 46 |
| P95 | 926 | 136 |
| P99 | 1.932,64 | 284 |
| Máximo | 7.015 | 981 |

A média superior à mediana e a distância até os máximos caracterizam uma distribuição assimétrica à direita. A maioria dos tickets é relativamente curta, enquanto uma pequena cauda contém textos muito longos.

- 49 tickets possuem até 3 palavras (0,10%).
- 57 possuem até 20 caracteres (0,12%).
- 482 alcançam ou excedem o P99 de palavras (aproximadamente 1,01%).
- 479 alcançam ou excedem o P99 de caracteres (aproximadamente 1,00%).

Os comprimentos variam entre classes. Hardware apresenta mediana de 32 palavras e P95 de 192; Storage, mediana de 21 e P95 de 101. Essa diferença deve ser conhecida em avaliações futuras, pois o comprimento pode tornar-se um sinal indireto da classe.

## Auditoria de duplicatas

Não foram encontrados pares exatos, textos brutos repetidos, textos repetidos após normalização conservadora de espaços ou textos normalizados com rótulos conflitantes.

Os arquivos de auditoria foram gerados somente com cabeçalho, documentando resultado zero. A verificação não cobre paráfrases, pequenas alterações lexicais ou trechos parcialmente repetidos.

## Achados consolidados

1. O dataset possui esquema simples e completo, sem valores obrigatórios ausentes.
2. As oito classes apresentam desbalanceamento relativo, com razão de 7,74.
3. O comprimento é assimétrico à direita e contém pequenas caudas de textos muito curtos e longos.
4. O perfil de comprimento varia por classe.
5. Não existem duplicatas determinísticas pelos critérios conservadores aplicados.
6. O conteúdo aparenta já ter passado por processamento anterior. Isso é uma observação, não comprovação do procedimento de origem.

## Limitações

- Não foi realizada auditoria semântica sistemática dos rótulos.
- Não foram procuradas quase duplicatas ou paráfrases.
- Não foi determinada a língua de cada ticket.
- Não foram medidos vocabulário, entidades, dados sensíveis ou qualidade linguística em escala.
- Não foram aplicadas transformações, exclusões ou correções.
- Não foram avaliados modelos nem estratégias de divisão dos dados.

## Encerramento

A análise exploratória está concluída dentro do escopo definido. Ela estabelece uma referência reproduzível sobre estrutura, completude, distribuição das classes, comprimento textual e duplicatas exatas. Pré-processamento, particionamento e modelagem são fases posteriores e independentes.

## Evidências detalhadas

- 01_dataset_overview/report.md: fonte, esquema, completude e classes.
- 02_text_length/report.md: distribuição de comprimento e extremos.
- 02_text_length/extreme_examples.csv: exemplos selecionados por comprimento.
- 03_duplicates/report.md: método e resultado da auditoria.
- 03_duplicates/exact_pair_duplicates.csv: pares exatos.
- 03_duplicates/normalized_duplicates.csv: repetições após normalização de espaços.
- 03_duplicates/conflicting_labels.csv: conflitos de rótulo.
