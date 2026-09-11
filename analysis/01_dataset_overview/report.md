# Etapa 1 - Visão geral do dataset

## Objetivo

Validar a fonte, identificar o contrato dos dados, medir a completude dos campos obrigatórios e descrever a distribuição da variável-alvo. Esta etapa não limpa dados nem toma decisões de modelagem.

## Fonte e reprodutibilidade

- Arquivo analisado: `all_tickets_processed_improved_v3.csv`
- Tamanho: 14,568,920 bytes
- Codificação utilizada: `utf-8`
- SHA-256: `044FDACE33FA564E1E60453F2941DAFC95539C99878B0D32746950394B9DD4D4`

O hash identifica exatamente a versão do arquivo que originou este relatório.

## Estrutura

- Registros lógicos: **47,837**
- Colunas: **2**
- Coluna de entrada: **`Document`**
- Coluna-alvo: **`Topic_group`**

| Coluna | Tipo | Nulos |
| --- | --- | --- |
| Document | str | 0 |
| Topic_group | str | 0 |

## Completude

- Textos nulos ou vazios: **0**
- Rótulos nulos ou vazios: **0**

Não foram aplicadas remoções. Um texto preenchido ainda pode ser curto, repetitivo ou pouco informativo; isso será investigado nas etapas seguintes.

## Exemplo estrutural

- `Document`: connection with icon icon dear please setup icon per icon engineers please let other details needed thanks lead
- `Topic_group`: Hardware

O conteúdo de `Document` aparenta ter sido previamente processado: o exemplo usa letras minúsculas, pouca pontuação e estrutura gramatical reduzida. Essa é uma hipótese inicial, não uma regra de limpeza.

## Distribuição das classes

| Classe | Quantidade | Percentual |
| --- | --- | --- |
| Hardware | 13617 | 28.47% |
| HR Support | 10915 | 22.82% |
| Access | 7125 | 14.89% |
| Miscellaneous | 7060 | 14.76% |
| Storage | 2777 | 5.81% |
| Purchase | 2464 | 5.15% |
| Internal Project | 2119 | 4.43% |
| Administrative rights | 1760 | 3.68% |

- Número de classes: **8**
- Maior classe: **Hardware**, com **13,617** registros
- Menor classe: **Administrative rights**, com **1,760** registros
- Razão entre maior e menor: **7.74**
- Baseline da classe majoritária: **28.47%** de acurácia

## Interpretação

O dataset é desbalanceado em termos relativos. A maior classe possui aproximadamente 7.74 vezes mais registros que a menor, e prever sempre `Hardware` já produziria 28.47% de acurácia. Portanto, acurácia isolada não será suficiente em uma avaliação futura.

Apesar do desbalanceamento, a menor classe ainda possui 1,760 exemplos. Não há evidência nesta etapa para aplicar oversampling, undersampling ou pesos de classe. Essas alternativas só devem ser comparadas durante a futura modelagem.

## Decisões e limites desta etapa

- A coluna `Document` será tratada como entrada textual.
- A coluna `Topic_group` será tratada como variável-alvo.
- Nenhuma linha será removida por ausência de texto ou rótulo.
- Nenhuma transformação textual foi aplicada.
- A análise de comprimento será feita separadamente na etapa 2.
- Duplicatas, qualidade semântica e decisões de pré-processamento permanecem em aberto.
