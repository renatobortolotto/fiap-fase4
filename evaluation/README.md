# Conjunto de desenvolvimento com dados reais

Este pool contém **17 avaliações reais** da Olist, selecionadas após inspeção do
texto para criar casos pequenos e reproduzíveis. Não é uma amostra aleatória,
um teste cego, uma avaliação humana independente ou uma estimativa da qualidade
da busca sobre os 42.687 documentos. Os rótulos foram propostos na implementação
com auxílio de IA e precisam de revisão da equipe.

As quatro perguntas temáticas têm julgamentos binários sobre todo este pool:

| Tema | Critério de relevância | Relevantes no pool |
| --- | --- | --- |
| atraso | Menção explícita a atraso ou prazo não cumprido | 4 |
| avaria | Produto danificado, quebrado ou que não funciona | 5 |
| elogio | Relato positivo de recebimento antes do prazo | 4 |
| faltante | Parte do pedido ou componente ausente, mesmo que resolvido depois | 5 |

Uma avaliação pode ser relevante para mais de uma pergunta. Nota baixa não foi
usada como sinônimo de reclamação: existe no pool um elogio textual com nota 1.
A quinta pergunta usa um período sem dados para testar o gate de recuperação vazio.

Para reproduzir a avaliação neste pool, crie um índice separado:

```powershell
.venv\Scripts\python.exe -m voc_olist index --documents evaluation\pool_documents.jsonl --index-dir artifacts\evaluation-index
.venv\Scripts\python.exe -m voc_olist evaluate --queries evaluation\questions.jsonl --index-dir artifacts\evaluation-index --top-k 4 --output reports\evaluation-pool.json
```

Para avaliar o índice principal, prepare outro conjunto com IDs relevantes reais,
mais temas, paráfrases, filtros e perguntas sem suporte. Separe perguntas para
calibrar o limiar das perguntas do teste final. Leia `docs/avaliacao.md`.

As métricas do pool avaliam somente a recuperação. A correção, a fundamentação
semântica e a abstenção do LLM exigem revisão das respostas completas.

Origem: [dataset Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce),
licença informada pelo Kaggle: CC BY-NC-SA 4.0. Os textos do pool são documentos
de origem, não fixtures sintéticas. Os testes de software em `tests/` usam fixtures
independentes e explicitamente controladas.

A licença e as transformações dos trechos de origem estão detalhadas em [DATA_NOTICE.md](../DATA_NOTICE.md).
