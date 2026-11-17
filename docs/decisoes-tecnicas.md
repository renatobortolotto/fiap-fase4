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

A codificação economiza trabalho sem alterar a unidade da base: 37.111 textos distintos representam 42.687 documentos. Os textos são ordenados por comprimento para os lotes de embeddings e os vetores são restaurados à ordem original dos documentos. Duas avaliações com texto igual mantêm IDs e metadados próprios no corpus. O dedup de contexto impede apenas repetir o mesmo texto várias vezes em uma resposta.

## Reordenação híbrida

A inspeção do pool de desenvolvimento revelou resultados semanticamente próximos, mas sem a menção específica pedida. Isso motivou combinar o ranking denso com BM25. `HybridIndex` calcula as estatísticas BM25 no corpus completo e pontua lexicalmente somente o pool elegível fornecido pela busca densa. Com a configuração padrão, são até 200 candidatos após filtros de metadados, deduplicação textual e limiar de cosseno. Se `top_k` for configurado acima de 200, o tamanho solicitado ao índice base cresce para atendê-lo.

Reciprocal Rank Fusion soma `1 / (60 + rank)` para os ranks denso e lexical com pesos iguais; contribuição lexical exige score BM25 positivo. Essa escolha evita tratar scores BM25 e cosseno como grandezas diretamente comparáveis. A similaridade exibida continua sendo o cosseno original, não uma confiança na resposta. A tokenização lexical remove acentos e algumas palavras funcionais, preservando negações; não realiza uma análise morfológica completa do português.

O modo padrão é `RETRIEVAL_MODE=hybrid`; `RETRIEVAL_MODE=dense` mantém a linha de base disponível. A implementação usa a biblioteca padrão e o índice NumPy existente. Seu limite é explícito: a reordenação não recupera documentos ausentes do pool denso e não garante melhor resultado em todas as perguntas.

Nos relatórios históricos do pool de 17 documentos, Recall@4 passou de 0,5625 na linha de base para 0,675 no modo híbrido; MRR@4 passou de 0,875 para 1,0. O ajuste foi motivado e avaliado no mesmo material de desenvolvimento, com rótulos propostos por IA. Esses números não são evidência independente de generalização, não validam a geração do LLM e não substituem uma execução final da revisão atual. O protocolo em `avaliacao.md` mantém a revisão humana e o teste separado como trabalhos pendentes.

## Filtros explícitos

Nota, período, categoria e atraso são seleções visíveis, aplicadas aos candidatos antes do ranking por similaridade. Anos explicitamente temporais na pergunta também geram recorte anual: “entregas em 2017” restringe `purchase_date` a 2017. O sistema intersecta esse recorte com o período manual e mostra/exporta os filtros efetivos. A interpretação procura distinguir datas de códigos de produto ou pedido. Nota, categoria e atraso não são inferidos silenciosamente do texto.

Uma pergunta sobre “clientes insatisfeitos” pode ser demonstrada com notas 1 e 2, explicando que essa é a definição operacional escolhida. O sistema não deve afirmar que todas as pessoas com essas notas têm o mesmo motivo de insatisfação.

## Abstenção

O limite inicial de cosseno 0,75 e a exigência de dois documentos distintos são configurações conservadoras a calibrar. O E5 tende a produzir scores relativamente altos, conforme a seção de perguntas frequentes de seu model card. Um score alto não equivale a uma probabilidade de correção.

A abstenção combina o `ScopeGuard`, a disponibilidade de evidências e a geração restrita ao contexto. O guard compara famílias de tarefas de compra e externas com E5, usando margem inicial 0,015, além de regras de agregações globais e períodos sem dados. A margem não foi calibrada como probabilidade de risco. Uma pergunta permitida ainda pode não ser respondível pelas evidências. Perguntas novas podem escapar dos controles ou ser recusadas indevidamente; o protocolo em `avaliacao.md` precisa medir esses dois tipos de erro.

As estatísticas do índice híbrido e os protótipos do guard permanecem em cache no serviço da sessão. A consulta não refaz a tokenização de todo o corpus nem a codificação das famílias a cada pergunta.

## LLM e saída estruturada

O padrão é [`Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M`](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF), revisão `bb5d59e06d9551d752d08b292a50eb208b07ab1f`, com runtime portátil [llama.cpp b12359](https://github.com/ggml-org/llama.cpp/releases/tag/b12359) em CPU e quatro threads. A quantização permite usar o modelo em formato GGUF local; os dois segmentos somam cerca de 4,68 GB. O runtime oficial tem aproximadamente 25 MB. Recomendam-se 16 GB de RAM e cerca de 10 GB livres em disco para a configuração padrão, com espaço adicional para outros caches.

O aplicativo obtém os arquivos e gerencia o próprio servidor llama.cpp oculto, restrito a `127.0.0.1` em porta temporária, encerrando seu processo ao sair do Python. A opção evita uma instalação global ou um servidor que o usuário precise iniciar manualmente. A API recebe o schema de resposta. Tamanho de modelo, quantização e formato válido não demonstram melhor sustentação: os pilotos e métricas finais dessa configuração ainda precisam de execução e inspeção.

O fallback opcional `Qwen/Qwen2.5-1.5B-Instruct`, revisão `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, usa Transformers e acrescenta cerca de 3,1 GB de download. Transformers 4.57.6 e Sentence Transformers 5.7.0 são as versões do lock compatível com LM Format Enforcer 0.11.3. Nesse caminho, o [decoder restrito](https://github.com/noamgat/lm-format-enforcer) controla o schema e alternativas de exemplos. Ollama com `qwen2.5:3b` continua outra alternativa. Cada provedor deve ser avaliado separadamente. Restringir formato resolve uma classe de erro estrutural, não a verdade da resposta.

O contrato `context-synthesis-v2` evita atribuir uma síntese ampla a um ou dois IDs escolhidos pelo modelo. `findings` traz uma ou duas sínteses; `context_evidence_ids`, definido pelo sistema, enumera todo o contexto, até oito fontes no padrão. O gerador recebe esse conjunto completo e seus metadados. `illustrative_quotes` oferece um ou dois trechos literais com sua fonte exata, sem apresentá-los como prova individual de todas as frases.

A auditoria do caso QA01 motivou essa separação: a síntese encontrava suporte no conjunto de oito avaliações consultadas, mas a atribuição anterior a E4/E6 cobria apenas parte de seu conteúdo. Não bastava verificar a existência desses IDs. A correção foi tornar explícito o contexto da síntese e separar exemplos de atribuição de prova. Esse diagnóstico é uma inspeção de desenvolvimento, não certificação semântica automática nem benchmark independente.

`literal_quotes_verified=true` confirma a origem textual dos exemplos por comparação normalizada; `summary_entailment_verified=false` declara que o sistema não certifica sustentação semântica da síntese. O revisor precisa ler todas as fontes relevantes do contexto, não só os exemplos ilustrativos.

## Instalação reproduzível no Windows

Os arquivos nativos ficam em `.cache/native`, com download retomável e conferência dos tamanhos e SHA-256 esperados. O runtime é portátil, sem instalação global ou privilégios de administrador. `python -m voc_olist models` antecipa a obtenção dos modelos e runtime sem preparar o corpus. O primeiro uso também pode obter os arquivos faltantes.

Para E5 e fallback Transformers, `model_store.py` usa download para `local_dir`, com arquivos normais, sem exigir symlinks. Caches legados completos são reutilizados e preservados. A revisão fixa modelos por commit, runtime por release e dependências no lock; instalação pip sem lock continua sendo uma alternativa com menor reprodutibilidade.

`Setup.ps1 -ArchivePath "C:\Dados Olist\archive.zip"` importa um ZIP local e implica preparação e indexação. O script cria as pastas de execução e preserva um `.env` existente. `.python-version` declara Python 3.12 e a pasta `artifacts` é mantida no Git com `.gitkeep`. Problemas iniciais de clone sem essa pasta e de texto acentuado no PowerShell motivaram ajustes; eles não equivalem a uma instalação fria completa já validada. O teste final de instalação desta revisão permanece pendente de registro.

## Limite de inferência de negócio

A seleção top-k favorece similaridade à pergunta e não constitui uma amostra aleatória do corpus. Portanto, “nos relatos recuperados aparecem atrasos” é uma formulação possível; “atraso é o principal problema de todos os clientes” requer outra análise. Rankings de temas e percentuais populacionais exigem classificação ou agregação sistemática com critérios e denominadores documentados.

## Reaproveitamento de projeto anterior

É possível reaproveitar organização de pastas, estilo visual, rotinas de configuração e padrões de documentação de um projeto anterior. Dados educacionais, modelos treinados para outro domínio e conclusões daquele projeto não validam o domínio Olist. Notas de avaliação de 1 a 5 também não são NPS e não devem ser convertidas automaticamente nesse indicador.

## Fonte dos dados

A referência do corpus é a [publicação da Olist no Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce/data). Registrar a versão obtida, a data do download e os hashes preserva a possibilidade de reproduzir a preparação. Antes da publicação pública, conferir as condições de uso e a atribuição na página da fonte; o repositório pode fornecer instruções de download em vez de redistribuir os arquivos brutos.
