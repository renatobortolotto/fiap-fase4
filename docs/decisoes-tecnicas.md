# Decisões técnicas e limites

## Unidade de conhecimento

Usar uma avaliação por pedido como documento preserva o relato e sua rastreabilidade. Título e comentário são combinados sem inventar texto para valores vazios. A nota é metadado; uma nota baixa não é, por si só, uma reclamação sobre entrega ou produto.

Não traduzimos nem corrigimos automaticamente o texto do cliente. A limpeza remove ruído de representação e espaços redundantes, preservando sinais como negação, acentos e pontuação úteis ao sentido. Registros sem texto são excluídos do corpus textual, com contagem no relatório de preparação. Uma mesma frase em pedidos distintos continua sendo uma observação distinta; remover tudo por igualdade de texto poderia apagar recorrência real.

Os metadados opcionais permitem restringir a recuperação. A data usada no filtro deve ser a data de compra documentada no campo `purchase_date`; a criação da avaliação tem outro significado. Pedidos com vários produtos mantêm uma lista de categorias, sem multiplicar a avaliação. Atraso desconhecido não é convertido em `false`.

## Embeddings locais

Escolhemos `intfloat/multilingual-e5-small` como ponto de partida para recuperação em português sem cobrança por consulta. Usamos os prefixos de recuperação e a normalização indicados no [model card oficial](https://huggingface.co/intfloat/multilingual-e5-small). O limite de entrada do modelo exige atenção a truncamento: se o corpus contiver textos longos, medir quantos são afetados antes de decidir entre truncar e dividir. Uma estratégia futura de chunks deve preservar IDs de origem e impedir que vários chunks de uma avaliação sejam contados como evidências independentes.

Não foi realizado fine-tuning como condição inicial. Primeiro deve ser estabelecida uma linha de base com julgamentos de relevância e erros observados. Resultados publicados do modelo em outros benchmarks não são resultados deste projeto.

## Índice simples e persistente

NumPy armazena a matriz normalizada; JSONL armazena os textos e metadados; um manifesto registra a configuração e a integridade. A busca exata facilita depuração e reprodução no volume inicial. Seu custo cresce com a quantidade de documentos. Um banco vetorial ou índice aproximado passa a ser uma opção quando medições justificarem a complexidade adicional.

## Reordenação híbrida

A inspeção do pool de desenvolvimento revelou resultados semanticamente próximos, mas sem a menção específica pedida. Isso motivou combinar o ranking denso com BM25. `HybridIndex` calcula as estatísticas BM25 no corpus completo e pontua lexicalmente somente o pool elegível fornecido pela busca densa. Com a configuração padrão, são até 200 candidatos após filtros de metadados, deduplicação textual e limiar de cosseno. Se `top_k` for configurado acima de 200, o tamanho solicitado ao índice base cresce para atendê-lo.

Reciprocal Rank Fusion soma `1 / (60 + rank)` para os ranks denso e lexical com pesos iguais; contribuição lexical exige score BM25 positivo. Essa escolha evita tratar scores BM25 e cosseno como grandezas diretamente comparáveis. A similaridade exibida continua sendo o cosseno original, não uma confiança na resposta. A tokenização lexical remove acentos e algumas palavras funcionais, preservando negações; não realiza uma análise morfológica completa do português.

O modo padrão é `RETRIEVAL_MODE=hybrid`; `RETRIEVAL_MODE=dense` mantém a linha de base disponível. A implementação usa a biblioteca padrão e o índice NumPy existente. Seu limite é explícito: a reordenação não recupera documentos ausentes do pool denso e não garante melhor resultado em todas as perguntas.

No pool de 17 documentos, Recall@4 passou de 0,5625 na linha de base para 0,675 no modo híbrido; MRR@4 passou de 0,875 para 1,0. O ajuste foi motivado e avaliado no mesmo material de desenvolvimento, com rótulos propostos por IA. Esses números não são evidência independente de generalização, nem validam a geração do LLM. O protocolo em `avaliacao.md` mantém a revisão humana e o teste final separado como trabalhos pendentes.

## Filtros explícitos

Nota, período, categoria e atraso são seleções visíveis, aplicadas aos candidatos antes do ranking por similaridade. Esse desenho evita depender de uma interpretação silenciosa do LLM para decidir o recorte. Uma pergunta sobre “clientes insatisfeitos” pode ser demonstrada com notas 1 e 2, explicando que essa é a definição operacional escolhida. O sistema não deve afirmar que todas as pessoas com essas notas têm o mesmo motivo de insatisfação.

## Abstenção

O limite inicial de cosseno 0,75 e a exigência de dois documentos distintos são configurações conservadoras a calibrar. O E5 tende a produzir scores relativamente altos, conforme a seção de perguntas frequentes de seu model card. Um score alto não equivale a uma probabilidade de correção.

A abstenção combina verificações de escopo, disponibilidade de evidências e geração restrita ao contexto. Perguntas novas podem escapar das verificações de escopo. Limiares também podem rejeitar perguntas válidas ou aceitar textos pouco pertinentes. O protocolo em `avaliacao.md` precisa medir esses dois tipos de erro.

## LLM e saída estruturada

Ollama permite executar a geração na máquina local. A API admite mensagens e formato JSON; o contrato usado está descrito na [documentação oficial do endpoint de chat](https://docs.ollama.com/api/chat). O `.env.example` utiliza `qwen2.5:3b`; a alternativa Transformers com `Qwen/Qwen2.5-0.5B-Instruct` permite rodar sem um servidor Ollama. Essa alternativa de poucos recursos tem capacidade limitada e pode se abster por falha de formato ou de fundamentação. Conferir o `.env` e a configuração exportada ao reproduzir resultados.

O modelo recebe apenas as evidências selecionadas, com rótulos curtos E1, E2 etc., nota, data de compra, categorias e atraso observado. As afirmações retornam esses rótulos em `evidence_ids`. A exportação mantém a associação de `citation_id` ao `doc_id` SHA-256 estável. Isso reduz a necessidade de o modelo copiar hashes longos e permite verificar a origem. Os rótulos curtos são locais a cada resposta.

Rejeitar citações inexistentes impede uma classe de erro estrutural. Não impede uma interpretação equivocada de uma fonte verdadeira. A sustentação semântica e a relevância das fontes devem ser revisadas por pessoas. Modelos pequenos podem falhar ao seguir o contrato; é preferível devolver uma falha explícita ou abstenção a aceitar uma resposta sem fontes.

## Limite de inferência de negócio

A seleção top-k favorece similaridade à pergunta e não constitui uma amostra aleatória do corpus. Portanto, “nos relatos recuperados aparecem atrasos” é uma formulação possível; “atraso é o principal problema de todos os clientes” requer outra análise. Rankings de temas e percentuais populacionais exigem classificação ou agregação sistemática com critérios e denominadores documentados.

## Reaproveitamento de projeto anterior

É possível reaproveitar organização de pastas, estilo visual, rotinas de configuração e padrões de documentação de um projeto anterior. Dados educacionais, modelos treinados para outro domínio e conclusões daquele projeto não validam o domínio Olist. Notas de avaliação de 1 a 5 também não são NPS e não devem ser convertidas automaticamente nesse indicador.

## Fonte dos dados

A referência do corpus é a [publicação da Olist no Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce/data). Registrar a versão obtida, a data do download e os hashes preserva a possibilidade de reproduzir a preparação. Antes da publicação pública, conferir as condições de uso e a atribuição na página da fonte; o repositório pode fornecer instruções de download em vez de redistribuir os arquivos brutos.
