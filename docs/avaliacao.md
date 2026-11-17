# Protocolo de avaliação

## O que este protocolo permite afirmar

Um teste de software aprovado demonstra o comportamento testado. Uma execução de ponta a ponta mostra que o pipeline funcionou naquele cenário. Nenhum desses resultados, isoladamente, demonstra que a recuperação é boa ou que as afirmações são sustentadas. A qualidade exige perguntas representativas, rótulos de relevância e revisão das respostas.

Os resultados históricos abaixo descrevem somente o pool incluído. A revisão `context-synthesis-v2`, com padrão Qwen2.5-7B-Instruct-GGUF Q4_K_M, runtime llama.cpp portátil, guard semântico e schema JSON, precisa de registros próprios. Pilotos e números finais dessa configuração, o ensaio de aceitação e a instalação limpa estão pendentes nesta documentação. Não transferir aprovações de contratos, modelos ou provedores anteriores para o padrão nativo.

## Conjunto de desenvolvimento incluído

`evaluation/pool_documents.jsonl` contém 17 avaliações reais selecionadas após inspeção de seus textos. `evaluation/questions.jsonl` contém quatro perguntas temáticas com rótulos de relevância propostos com auxílio de IA e uma pergunta com filtro de período a partir de 2040, sem documentos. Os critérios e a origem estão em `evaluation/README.md`.

Esse material é um pool pequeno de desenvolvimento, com rótulos pendentes de revisão humana. Não é teste independente, amostra aleatória nem medição da qualidade de busca no corpus principal. Os rótulos cobrem o pool de 17 documentos segundo os critérios propostos; podem conter erros. Uma métrica calculada sobre eles descreve concordância com esses rótulos, sem estabelecer qualidade validada por pessoas.

Para executar sem misturar o pool com o índice principal:

```powershell
.venv\Scripts\python.exe -m voc_olist index --documents evaluation/pool_documents.jsonl --index-dir artifacts/evaluation-index
$env:RETRIEVAL_MODE = "dense"
.venv\Scripts\python.exe -m voc_olist evaluate --queries evaluation/questions.jsonl --index-dir artifacts/evaluation-index --top-k 4 --output reports/review-20261116/retrieval-dense.json
$env:RETRIEVAL_MODE = "hybrid"
.venv\Scripts\python.exe -m voc_olist evaluate --queries evaluation/questions.jsonl --index-dir artifacts/evaluation-index --top-k 4 --output reports/review-20261116/retrieval-hybrid.json
```

As execuções históricas usaram `top_k=4` e limiar de cosseno 0,75:

| Modo | Recall@4, 4 perguntas com relevância | MRR@4, 4 perguntas com relevância | Acertos do gate, 5 perguntas |
| --- | --- | --- | --- |
| Denso | 0,5625 | 0,875 | 5/5 |
| Híbrido | 0,675 | 1,0 | 5/5 |

Os arquivos históricos são `reports/evaluation-dense-initial.json` e `reports/evaluation-pool.json`; eles são preservados sem reescrita. Os comandos acima geram novos relatórios em uma pasta própria da revisão. A reordenação híbrida combina ranks denso e BM25 por RRF, constante 60 e pesos iguais, dentro do pool denso elegível. Ela foi introduzida após observar erros neste mesmo material. A melhora observada é um resultado de desenvolvimento, não de um teste reservado. O acerto do gate considera somente a quantidade de hits e não mede o guard ou o LLM.

Revisar os rótulos, preservar as correções e ampliar o conjunto antes de apresentar o resultado como avaliação de qualidade. Os passos abaixo descrevem esse trabalho adicional.

## 1. Verificação do software

Executar os testes disponíveis e inspecionar os seguintes casos:

| Área | Caso | Comportamento esperado |
| --- | --- | --- |
| Preparação | Título e comentário vazios | Excluir do corpus textual e contar o descarte |
| Preparação | Texto somente no título | Preservar a evidência |
| Preparação | Mesmo pedido com vários itens | Não multiplicar a avaliação |
| Preparação | Datas de entrega ausentes | Manter atraso desconhecido |
| Persistência | Documento ou matriz alterados | Detectar incompatibilidade de integridade |
| Filtros | Nota, período, categoria e atraso | Retornar apenas documentos compatíveis |
| Recuperação | Recorte sem documentos | Abster-se com motivo |
| Escopo | Ano temporal explícito | Aplicar e exportar o filtro anual efetivo |
| Escopo | Código de produto com quatro dígitos | Não presumir que seja período de compra |
| Saída | Exemplo com ID de fonte inexistente | Rejeitar a resposta inválida |
| Saída | Trecho ausente na fonte indicada | Rejeitar, sem transferir silenciosamente a outra fonte |
| Saída | Síntese com rótulos E1/E2 individuais | Rejeitar a atribuição incompatível com o contrato |
| Contexto | Até oito fontes recuperadas | Enviar e exportar todo o contexto efetivamente consultado |
| Dados adversariais | Comentário contendo instruções ao modelo | Tratar como texto da avaliação |

Também verificar instalação de clone sem artefatos, `.env` preservado, ZIP local com espaços no caminho, download nativo retomável com tamanho e SHA-256 verificados e cache do encoder sem privilégios de symlink. Conferir `models`, início do processo gerenciado em loopback, reutilização e encerramento ao sair do Python. Falhas iniciais de pasta `artifacts` ausente e de acentos no PowerShell motivaram correções; somente uma nova execução completa pode confirmar o fluxo corrigido. A existência das correções não é prova de instalação fria concluída.

Testes com dados sintéticos devem ser identificados como tais. Eles são úteis para controlar casos de borda e não substituem a avaliação sobre Olist.

## 2. Conjunto de perguntas e relevância

Criar um conjunto inicial de pelo menos 30 perguntas, incluindo consultas sobre entrega, produto, atendimento, elogios e consultas com metadados. Incluir perguntas específicas e amplas, negativas e positivas, além de casos não respondíveis. A quantidade é uma proposta operacional, não um requisito numérico do enunciado.

Separar as perguntas antes de ajustar parâmetros: um conjunto de desenvolvimento para decisões e um conjunto final reservado. Não escolher limiar, top-k ou prompt olhando os resultados finais e depois tratá-los como avaliação independente.

Para cada pergunta respondível, pessoas revisam candidatos recuperados por mais de uma configuração e registram quais documentos realmente ajudam a responder. Usar os `doc_id` persistentes do corpus em `relevant_ids`, nunca os rótulos E1/E2 de uma resposta. É desejável que duas pessoas rotulem uma parte em comum e conciliem discordâncias. O conjunto deve guardar a pergunta, o recorte, a identificação das evidências relevantes e uma justificativa curta. Esse trabalho humano continua pendente; os rótulos propostos por IA não o substituem.

Não confundir as fontes retornadas pelo próprio sistema com rótulos de referência. Quando o julgamento cobrir somente um pool de candidatos, a cobertura é parcial e essa limitação deve acompanhar as métricas.

## 3. Recuperação

Executar `python -m voc_olist evaluate --help` para os parâmetros. Cada linha JSONL contém `query_id` único, `question` e, opcionalmente, `relevant_ids`, `expect_abstain` booleano e `filters`. O programa calcula métricas contra os rótulos fornecidos, sem verificar sua origem; registrar se foram propostos por IA ou revisados por pessoas. IDs inexistentes no índice e perguntas com identificadores duplicados são rejeitados.

- **Recall@k:** quantidade de documentos relevantes encontrados entre os primeiros k dividida pela quantidade de relevantes conhecidos para a pergunta.
- **MRR@k:** média do inverso da posição do primeiro documento relevante nos primeiros k resultados; zero quando nenhum é encontrado.

O relatório inclui `n_relevance_queries` como denominador das médias de relevância. Consultas sem `relevant_ids` ou com lista vazia têm métricas de relevância nulas. Cada resultado preserva os hits e scores, a quantidade de relevantes conhecidos e a quantidade recuperada. No relatório de avaliação, `hits[].id` contém o `doc_id` estável, não o `citation_id` E1/E2 usado pela geração. A ausência de rótulos não é convertida em desempenho zero.

`retrieval_gate_abstention_accuracy` mede apenas se a busca produziu menos de dois hits, em comparação com `expect_abstain`. `n_abstention_correct` e `n_abstention_queries` explicitam seu numerador e denominador. Não há execução de LLM nem do detector de escopo nesse cálculo. A quinta pergunta do pool verifica o gate com recorte vazio, sem demonstrar a abstenção de ponta a ponta para outras perguntas.

Registrar k, limiar, filtros, quantidade de perguntas e cobertura dos rótulos. Informar o denominador: perguntas sem rótulos não podem receber nota zero nem entrar silenciosamente na média. Relatar falhas por tema, pois uma média pode ocultar consultas ruins sobre um assunto específico.

Ao comparar os modos, manter os mesmos documentos, perguntas, filtros e limiar. Registrar `RETRIEVAL_MODE`. No híbrido, lembrar que BM25 pode apenas reordenar os candidatos densos elegíveis; um relevante fora desse pool permanece irrecuperável nessa consulta. O limiar continua sendo aplicado ao cosseno, não ao score de fusão.

## 4. Fundamentação da geração

Revisores avaliam cada afirmação gerada com acesso às fontes. Registrar separadamente:

1. **Formato:** `findings`, contexto e exemplos obedecem a `context-synthesis-v2`?
2. **Origem literal:** cada `illustrative_quote` consta no `context_text` da fonte exata indicada, por comparação normalizada?
3. **Contexto completo:** `context_evidence_ids`, definido pelo sistema, enumera todas as fontes efetivamente enviadas ao modelo e mapeia aos `doc_id` corretos?
4. **Sustentação semântica:** todas as partes de cada síntese são sustentadas pelo conjunto completo, com hipóteses, opiniões e situações pendentes preservadas?
5. **Relevância e escopo:** a síntese responde à pergunta e respeita filtros e período, sem extrapolar para a população?

O padrão nativo envia o schema ao llama.cpp local; o fallback Transformers usa LM Format Enforcer. Restrições de saída controlam forma e escolhas permitidas, não sustentação semântica. Uma execução interrompida ainda pode falhar na validação; o sistema não deve publicar uma resposta inválida. `literal_quotes_verified=true` confirma origem dos exemplos, enquanto `summary_entailment_verified=false` explicita que não existe certificação automática da síntese.

O contrato não atribui IDs isolados a cada frase de `findings`. Os exemplos são ilustrativos e não precisam, sozinhos, sustentar a síntese inteira. Na auditoria de desenvolvimento do caso QA01, o contexto de oito fontes apoiava a síntese, mas os antigos IDs E4/E6 cobriam apenas parte dela. Esse achado motivou a separação entre contexto global e exemplos; não constitui aprovação semântica automática.

Contar trechos de síntese sem suporte, hipóteses promovidas a fatos, desfechos inventados e generalizações indevidas. Um exemplo literal verdadeiro pode acompanhar uma interpretação equivocada. A revisão precisa ler o contexto completo, não avaliar somente os exemplos selecionados.

Exemplo de erro de escopo: comentários sobre atrasos recuperados para uma pergunta não sustentam “atraso é a principal reclamação de todos os clientes”. Uma resposta aceitável pode dizer que “há relatos de atraso nas avaliações recuperadas”, citando os casos específicos.

## 5. Abstenção

Incluir pelo menos estes cenários e paráfrases que não tenham sido usadas para criar regras:

| Pergunta/cenário | Expectativa |
| --- | --- |
| “Qual será o faturamento da empresa em 2027?” | Reconhecer ausência de suporte para previsão |
| “Como está o clima em São Paulo hoje?” | Reconhecer tema externo ao corpus |
| Pergunta válida com período/categoria sem dados | Explicar a ausência de resultados no recorte |
| Tema não sustentado pelos comentários recuperados | Abster-se ou pedir um recorte mais adequado |
| Pergunta válida e evidências adequadas | Responder com fontes, sem recusa desnecessária |

Medir respostas indevidas entre casos não respondíveis e recusas indevidas entre casos respondíveis. Não selecionar somente exemplos fáceis. Uma lista de termos proibidos não comprova generalização para perguntas externas novas.

O novo `ScopeGuard` usa famílias de tarefas E5 e margem inicial 0,015, além de regras de capacidade e período. Avaliar também fronteiras de intenção: “o que compradores relatam sobre instalar o produto?” pode estar no escopo; pedir código para instalar um programa é tarefa externa. A margem não é probabilidade nem foi validada como limiar universal. Confirmar que a admissão pelo guard não impede o LLM de se abster sobre um tema sem evidências.

## Ensaio de aceitação desta revisão

Está previsto um conjunto de 24 casos com execução real e inspeção assistida por IA, seguido de leitura pelo revisor. Os resultados finais ainda estão pendentes. O ensaio deve cobrir temas respondíveis, ausência de suporte, tarefas externas, agregações não implementadas, períodos, conflitos de filtros e instruções contidas em comentários.

Para cada caso, preservar pergunta, filtros solicitados e efetivos, decisão do guard, configuração do modelo e revisão, todas as fontes do contexto, sínteses, exemplos, tentativas, erros e duração. O relatório deve separar expectativa proposta, resposta efetiva e parecer de inspeção, citando o trecho do contexto que motivou o parecer. Um rótulo automático de aprovação não é julgamento humano.

Esse ensaio é aceitação de desenvolvimento, não benchmark independente ou teste cego. Uma leitura posterior por pessoa deve ser registrada como etapa própria, sem ser presumida pela criação do relatório. Nenhuma taxa final, quantidade de testes aprovados ou qualidade global desta revisão é afirmada antes da execução e conferência dos artefatos.

## 6. Calibração e desempenho

O limiar inicial 0,75 e o mínimo de dois documentos distintos ainda não são uma garantia de relevância. Comparar configurações no conjunto de desenvolvimento e observar o equilíbrio entre respostas sem suporte e recusas desnecessárias. Congelar a configuração antes de executar o conjunto final.

Registrar tempo de preparação, indexação, recuperação e geração; quantidade de documentos e textos distintos; modelo exato, quantização e revisão; CPU/GPU e memória; versão e hash do runtime; Python e bibliotecas. O padrão é Qwen2.5-7B-Instruct-GGUF Q4_K_M, revisão `bb5d59e06d9551d752d08b292a50eb208b07ab1f`, com llama.cpp b12359 e quatro threads de CPU. A instalação orienta 16 GB de RAM e cerca de 10 GB livres; medir o consumo real no ambiente avaliado.

O fallback Transformers 1,5B usa o lock com Transformers 4.57.6, Sentence Transformers 5.7.0 e LM Format Enforcer 0.11.3. Separar primeiro download, início do servidor, carregamento frio e consultas com cache. Não reaproveitar como medição atual tempos de modelos ou índices anteriores. Comparar os provedores somente se medidos nas mesmas perguntas, com julgamentos de sustentação sobre o contexto completo. Nenhum ganho de qualidade é presumido pela troca para 7B.

## Registro mínimo do relatório

| Campo | Preencher com dado real |
| --- | --- |
| Data, versão do código e hashes do corpus/índice | Pendente de execução |
| Modelo de embeddings e modelo gerador | Pendente de execução |
| Parâmetros de recuperação e filtros | Pendente de execução |
| Perguntas de desenvolvimento e finais | Pendente de rotulagem |
| Quantidade de perguntas e cobertura dos rótulos | Pendente de rotulagem |
| Recall@k / MRR@k | Histórico do pool acima; nova execução e teste independente pendentes |
| Sínteses revisadas contra o contexto completo | Aceitação assistida por IA e leitura humana final pendentes |
| Respostas e recusas indevidas | Não medidas neste documento |
| Tempos, equipamento e falhas conhecidas | Pendente de execução |

Guardar também exemplos de falha e suas fontes. Os campos “pendente” da tabela orientam um relatório final independente; o pool de desenvolvimento incluído não os torna automaticamente concluídos. Um relatório honesto deve distinguir o que foi medido, o que foi apenas implementado e o que continua pendente.
