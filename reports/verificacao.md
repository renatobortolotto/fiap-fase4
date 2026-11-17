# Verificação técnica da solução

Registro local: 2026-11-16T23:41:30.903103-03:00. UTC: 2026-11-17T02:41:30.903103+00:00.

Esta revisão consolida testes de software, instalação em clone novo, consultas reais e leitura assistida por IA das fontes. O código do runtime validado é `1bcc44273ada42784e1571880eb63da715c79339`; documentação e perguntas de demonstração foram finalizadas depois, sem alterar esse RAG. A proveniência e os hashes estão em [execution-provenance.json](review-20261116/execution-provenance.json). O registro anterior foi preservado em [verificacao-20261115.md](verificacao-20261115.md) e no [JSON histórico](verificacao-20261115.json).

## Configuração e dados

Padrão: `Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M`, revisão `bb5d59e06d9551d752d08b292a50eb208b07ab1f`, com llama.cpp portátil b12359 e quatro threads de CPU. Encoder: `intfloat/multilingual-e5-small`, revisão `614241f622f53c4eeff9890bdc4f31cfecc418b3`. O teste frio usou duas threads para encoder e gerador. Os downloads fixam tamanho e SHA-256; os assets esperados constam no JSON de verificação e na proveniência.

A preparação do ZIP oficial produziu 42.687 documentos a partir de 99.224 avaliações, excluindo 56.537 registros sem texto. O índice tem 42.687 × 384 valores; a codificação reaproveita 37.111 textos distintos, sem remover documentos de pedidos diferentes. O SHA-256 de `documents.jsonl` é `bc06619eadd964af277651083498f0adec336b6f4e8c6eae8e08e7bd719b2a4c`.

A busca híbrida reordena candidatos densos elegíveis com BM25/RRF. Filtros, limiar de cosseno e deduplicação textual são respeitados antes da seleção. A comparação do índice reconstruído reproduziu os mesmos contextos ordenados, códigos de escopo e filtros efetivos nos 24 casos: [cold-context-comparison.json](review-20261116/cold-context-comparison.json). Essa comparação não gerou outras respostas nem uma nova nota semântica.

## Testes de software

| Ambiente | Python | Resultado | Tempo |
| --- | --- | --- | --- |
| Clone técnico de revisão, código 1bcc442 | 3.12.14 | 288 passaram, sem falhas | 12,27 s |
| Clone Windows com instalação nova, código 1bcc442 | 3.12.13 | 288 passaram, sem falhas, erros ou skips | 9,719 s |
| Pasta definitiva fase4, código 1bcc442 | 3.12.14 | 288 passaram, sem falhas | 6,99 s |

Comandos e evidências: [unit-tests.json](review-20261116/unit-tests.json), [clean-install.json](review-20261116/clean-install.json) e [JUnit do clone novo](review-20261116/cold-pytest.xml). As fixtures controladas verificam dados, joins, índice, filtros, escopo, contrato, runtime e interface; não entram no corpus oficial. Esses resultados não são uma métrica de correção de respostas em linguagem natural.

Dependências observadas: torch 2.15.0+cpu, Transformers 4.57.6, Sentence Transformers 5.7.0, LM Format Enforcer 0.11.3, NumPy 2.5.4, Streamlit 1.67.0 e pytest 9.2.0.

## Instalação nova e interface real

O [registro frio](review-20261116/clean-install.json) partiu de clone GitHub sem venv, `.env`, CSVs, índice ou cache de modelos. O uv obteve CPython 3.12.13 e criou o ambiente; somente seu cache de wheels foi reutilizado. Não foram copiados pesos ou índice de uma instalação existente. O instalador começou no commit `64496ee`; antes dos testes e da interface, o clone foi atualizado para `1bcc442`, sem alteração do lock.

Comando executado: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Setup.ps1 -ArchivePath "archive (3).zip"`.

| Etapa | Tempo observado |
| --- | --- |
| Setup completo, saída 0 | 1.679,859 s, cerca de 27 min 59,9 s |
| Download frio do encoder E5 | 1.122 s, cerca de 18 min 42 s |
| Construção do índice, duas threads | 321,39 s |
| Assets nativos novos, com verificações | 181,884 s |

O download E5 foi o gargalo desta conexão; esses tempos não são mínimos de hardware nem promessa de desempenho. A recomendação operacional é Windows x64, 16 GB de RAM e 20 GB de disco livre, incluindo partes temporárias dos downloads.

Streamlit AppTest executou uma conversa real com o provedor nativo, offline, notas 4–5 e corpus completo: `answered`, oito fontes, um finding e um exemplo com origem literal conferida. O serviço levou 29,711 s; não houve exceção antes ou depois da consulta. O botão de exportação foi renderizado e seu payload foi salvo em [cold-ui-response.json](review-20261116/cold-ui-response.json); o resumo está em [cold-ui-smoke.json](review-20261116/cold-ui-smoke.json). O processo nativo foi encerrado e não restaram processos pertencentes ao teste.

AppTest verifica execução e interação de widgets no lado do servidor. Não houve inspeção por screenshot nem simulação de clique de download no navegador. O fallback de instalação somente com pip e outros sistemas/provedores não foram validados por esse ensaio frio.

## Pasta efetiva do usuário

Após atualizar a instalação efetiva, a suíte repetiu os 288 testes em 6,99 s. A saída foi preservada em [installed-pytest-output.txt](review-20261116/installed-pytest-output.txt) e [JUnit](review-20261116/installed-pytest.xml). A consulta CLI nativa sobre cobrança duplicada retornou `answered`, oito fontes e exemplo literal, em 29,867 s: [installed-smoke.json](review-20261116/installed-smoke.json).

A página Streamlit e seu endpoint de saúde responderam HTTP 200; o servidor foi encerrado depois. O [registro operacional](review-20261116/installed-runtime-check.json) distingue esse health check da interação real de widgets já executada pelo AppTest no clone frio. O smoke da pasta efetiva não amplia os 24 casos de aceitação nem mede qualidade estatística.

## Aceitação técnica v4

O [lote final](review-20261116/native-acceptance-v4.json) executou 24 casos reais do protocolo de desenvolvimento: nove positivos responderam; treze recusas obrigatórias se abstiveram; os dois condicionais também se abstiveram adequadamente ao suporte observado. Houve compatibilidade formal de status em 24/24 casos. Isso não é taxa de acurácia semântica.

O [parecer assistido das fontes](review-20261116/assistant-source-review-v4.md) confrontou cada síntese com todo o contexto e recebeu contraponto de um segundo agente nos nove positivos. Os dez findings foram classificados como sustentados; nove foram diretamente pertinentes e um incluiu informação lateral. Os doze exemplos tiveram origem literal normalizada válida; um era pouco ilustrativo. Não se observaram erros materiais ou violações de filtros nesse lote v4.

Há ressalvas de cobertura: QA03/QA05 são genéricos, QA02 inclui pontualidade lateral à pergunta sobre características do produto, e alguns exemplos são menos claros que outras fontes disponíveis. Esse parecer é revisão assistida por IA dos casos observados durante o desenvolvimento, não avaliação humana, conjunto cego ou benchmark independente. Não certifica consultas futuras.

As falhas e correções permanecem visíveis nos lotes e pareceres anteriores: v1 teve duração inventada bloqueada e causa operacional inferida; v2 inferiu desfecho ausente em QA10; v3 acrescentou “comuns” sem medir prevalência. Esses acréscimos não se repetiram no v4 observado. As saídas anteriores não foram reescritas como aprovadas.

## Demonstrações reais

| Exemplo | Artefato | Resultado | Tempo |
| --- | --- | --- | --- |
| Problemas concretos de entrega, notas 1–2 | [01-entrega.json](demo-detalhado/01-entrega.json) | answered, oito fontes | 28,252 s |
| Aspectos satisfatórios da entrega em 2017, notas 4–5 | [02-elogios.json](demo-detalhado/02-elogios.json) | answered, oito fontes | 8,899 s |
| Contagem global solicitada | [03-fora-do-escopo.json](demo-context-v2-final/03-fora-do-escopo.json) | abstained | 0,000 s |
| Período 2040 sem dados | [04-sem-evidencias.json](demo-context-v2-final/04-sem-evidencias.json) | abstained | 0,000 s |

O [parecer das perguntas específicas](review-20261116/focused-demo-source-review.md) encontrou suporte nas duas sínteses e origem literal/pertinente nos dois exemplos, com filtros respeitados. A primeira síntese aponta atraso e falta de informação no rastreamento; a segunda, rapidez e satisfação. São respostas concisas e de cobertura parcial, não análises abrangentes. As demonstrações de perguntas mais amplas e suas limitações também foram [preservadas](review-20261116/demo-source-review.md). Essas consultas não aumentam o denominador dos 24 casos técnicos.

## Alcance dos controles e limites

O contrato `context-synthesis-v2` atribui a síntese ao contexto completo em `context_evidence_ids` e separa `illustrative_quotes`. `literal_quotes_verified=true` confirma origem de exemplos; `summary_entailment_verified=false` permanece explícito. Schema válido, hash íntegro e exemplo literal não certificam a interpretação.

O pool histórico de 17 documentos e cinco consultas mantém Recall@4/MRR@4 de 0,5625/0,875 na busca densa e 0,675/1,0 na híbrida, com gate 5/5. Seus rótulos foram propostos por IA e o gate mede somente menos de dois hits. Esses valores não estimam qualidade do corpus inteiro nem do LLM.

O top-k não permite frequência, porcentagens ou rankings populacionais de temas. Os limiares 0,75 e 0,015 são heurísticas de desenvolvimento. A interpretação temporal automática cobre anos; meses e dias usam filtros manuais. Qualidade de provedores alternativos, benchmark independente, rótulos humanos e calibração separada são melhorias futuras, não requisitos extras do enunciado.

## Publicação e entrega

Endereço de entrega: [GitHub main](https://github.com/renatobortolotto/fiap-fase4/tree/main). O estado da sincronização/publicação é registrado no campo `publication` de [verificacao.json](verificacao.json), após ser observado; a validação técnica não pressupõe esse passo. Vídeo de até sete minutos e submissão acadêmica ainda cabem à equipe. Consulte [entrega](../docs/entrega.md), [roteiro](../docs/roteiro-video.md) e [checklist](../docs/checklist-entrega.md).
