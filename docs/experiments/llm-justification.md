# Experimento opcional: justificativa por LLM

## Status

Protótipo preservado para estudo, mas removido da interface, do Docker e das dependências oficiais. O classificador entregue usa somente a justificativa determinística baseada em contribuições TF-IDF.

## Teste manual de 12 de setembro de 2026

Foram usados seis tickets reais: o menor e o maior ticket do teste, uma classe majoritária, uma minoritária e duas classes adicionais. O caminho configurado falhou porque `gemini-2.5-flash-lite` não está disponível para novos usuários e o timeout de 8 segundos é menor que o mínimo de 10 segundos exigido pela API atual.

Para avaliar a ideia sem modificar o repositório, o mesmo adaptador foi executado em memória com `gemini-3.5-flash-lite` e timeout de 20 segundos. Quatro chamadas tiveram sucesso, mas produziram conteúdo igual ao determinístico, com diferenças apenas de aspas ou pontuação. Duas chamadas falharam com HTTP 503 e 504 e acionaram corretamente o fallback determinístico.

Também foram simuladas chave ausente, API indisponível e resposta inválida. Nos três casos, o sistema preservou o formato público `{"class": "...", "justification": "..."}` e retornou a justificativa determinística.

## Decisão

Não há evidência de ganho qualitativo que justifique custo, latência, indisponibilidade e exposição de dados a um serviço externo. O protótipo permanece em `src/ticket_classifier/justification/llm_optional.py`, seus testes permanecem em `tests/test_llm_justification.py` e suas dependências podem ser instaladas separadamente com `pip install -e ".[llm]"`. Isso não ativa a funcionalidade na aplicação oficial.

Uma futura reavaliação deve primeiro atualizar modelo, timeout e API do provedor; depois executar avaliação humana cega sobre os 200 tickets, medir taxa de falha, latência e custo, e revisar requisitos de privacidade. Somente um ganho consistente justificaria reintegrar essa camada.