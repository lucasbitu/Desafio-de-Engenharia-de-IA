# Etapa 3 - Auditoria de duplicatas

## Objetivo

Identificar repetições determinísticas e conflitos de rótulo antes de qualquer limpeza ou divisão entre treino e avaliação. Esta etapa não remove nem altera registros.

## Fonte e método

- Arquivo analisado: `all_tickets_processed_improved_v3.csv`
- Codificação utilizada: `utf-8`
- Registros analisados: **47,837**
- Linha de origem: número físico aproximado no CSV, considerando o cabeçalho como linha 1
- Normalização de auditoria: remoção de espaços externos e substituição de sequências de espaços por um único espaço

A normalização não altera caixa, pontuação, ordem ou conteúdo lexical. Portanto, ela detecta apenas diferenças de espaçamento, não similaridade semântica.

## Resultados

| Controle | Grupos | Registros envolvidos | Percentual dos registros |
| --- | ---: | ---: | ---: |
| Mesmo texto bruto e mesmo rótulo | não aplicável | 0 | 0.0000% |
| Excesso removível mantendo uma ocorrência por par exato | não aplicável | 0 | 0.0000% |
| Mesmo texto bruto, independentemente do rótulo | 0 | 0 | 0.0000% |
| Mesmo texto após normalizar espaços | 0 | 0 | 0.0000% |
| Texto normalizado repetido com o mesmo rótulo | não aplicável | 0 | 0.0000% |
| Texto normalizado com rótulos conflitantes | 0 | 0 | 0.0000% |

## Como interpretar cada controle

### Mesmo texto e mesmo rótulo

São cópias exatas do mesmo exemplo supervisionado. Podem super-representar um padrão e causar vazamento se cópias forem distribuídas entre treino e avaliação. Remoção ainda exige uma decisão explícita.

### Mesmo texto com rótulos diferentes

É um conflito de supervisão. O mesmo conteúdo não fornece informação suficiente para escolher duas classes distintas. Esses casos exigem revisão de rótulo, contexto ou taxonomia; não devem ser resolvidos escolhendo uma classe arbitrariamente.

### Igualdade após normalização de espaços

Detecta registros cujo conteúdo difere apenas por espaços ou quebras de linha. A normalização é conservadora e usada somente para comparação.

## Arquivos de auditoria

- `exact_pair_duplicates.csv`: registros com texto bruto e rótulo exatamente iguais
- `normalized_duplicates.csv`: textos repetidos após normalização de espaços
- `conflicting_labels.csv`: textos normalizados associados a mais de um rótulo

Arquivos sem ocorrências são gerados apenas com cabeçalho. Isso documenta que o controle foi executado e encontrou zero casos.

## Limites desta etapa

- Não detecta paráfrases ou pequenas alterações lexicais.
- Não detecta cadeias de e-mail parcialmente repetidas.
- Não calcula similaridade por TF-IDF, embeddings ou distância de edição.
- Não autoriza remoção automática de registros.
- Quase duplicatas devem ser tratadas como análise posterior, separada dos controles exatos.

## Decisão antes do futuro split

Se existirem duplicatas, todas as ocorrências do mesmo grupo devem permanecer na mesma partição ou ser deduplicadas antes da divisão. Caso contrário, a avaliação poderá medir memorização em vez de generalização.
