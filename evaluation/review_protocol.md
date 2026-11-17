# Protocolo técnico de aceitação das respostas

Protocolo de revisão, versão 3, de 16/11/2026, adaptado ao contrato context-synthesis-v2. As definições das perguntas permanecem na versão 2: nove casos positivos que exigem resposta, dois casos condicionais e treze casos de recusa necessária. As definições foram revistas após inspeção técnica de fontes e observação do piloto; este é um conjunto de desenvolvimento observado. Relatórios já gerados não devem ser sobrescritos nem receber aprovação retroativa com outra versão das definições.

Este conjunto contém 24 casos preparados por revisão assistida por IA a partir dos requisitos do desafio e das limitações observadas no sistema. É um conjunto técnico de aceitação e desenvolvimento: não contém rótulos humanos, não constitui um benchmark cego e não mede, por si só, a qualidade na população de perguntas dos usuários. Nenhum modelo de linguagem foi chamado para produzir respostas nesta preparação.

## Composição e proveniência

| Grupo | Casos | Objetivo |
|---|---|---|
| Qualitativas dentro do domínio | QA01–QA10 (10) | Seleção de temas, pertinência das fontes, notas, atendimento, avaria, item faltante, cobrança dupla e filtros válidos |
| Exteriores ou com informação ausente | QA11–QA18 (8) | Recusar conhecimento externo, dados atuais, identificação pessoal, política interna e causa não comprovada |
| Limites da base e da pergunta | QA19–QA24 (6) | Datas de 2025, contagem/percentual globais, ranking geográfico, recorte vazio e ambiguidade |

Os filtros usam os campos efetivamente disponíveis: score_min/score_max, category, date_from/date_to e delivered_late. A categoria beleza_saude foi conferida no índice atual de 42.687 documentos. Os filtros temporais referem-se à data da compra (purchase_date), não à data da avaliação. Os recortes de 2015 e 2025 foram escolhidos para serem vazios no corpus histórico atual.

Não foram construídos conjuntos sistemáticos de IDs relevantes ou julgamentos de relevância por documento. Criar esses rótulos seria uma atividade distinta. A conferência pontual da respondibilidade de QA07 não equivale a uma base rotulada de recuperação. Portanto, este arquivo não permite calcular Recall@k, MRR ou precisão da recuperação. A qualidade exige a leitura das fontes de cada resposta e a aplicação da rubrica abaixo.

As perguntas não repetem os textos exatos dos exemplos atuais nem das 12 perguntas da auditoria inicial. Várias são variações deliberadas de intenções próximas: isso verifica se a resposta depende do significado em vez da memorização de uma frase de demonstração.

## Formato dos casos

Cada linha de review_questions.jsonl é um objeto com query_id, category, question, allowed_statuses, expected_answerable e expectation; filters aparece quando necessário. allowed_statuses contém somente answered e/ou abstained. Esse campo testa o formato do resultado, não substitui a avaliação do conteúdo.

QA01–QA09 têm expected_answerable=true e allowed_statuses=["answered"]. São os nove casos positivos desta versão: uma recusa injustificada deve falhar em utilidade, em vez de ser contabilizada como aprovação. QA01 apresentou fontes suficientes no piloto, mas o gerador se recusou; esse resultado é uma falha observada, não uma abstenção aprovada.

QA07 foi conferida sem geração por LLM: com a busca híbrida atual, top_k=8, min_similarity=0,75 e o índice de 42.687 documentos, a sexta fonte declara explicitamente que passaram duas vezes o cartão. As outras fontes próximas tratam de parcelamento, fretes e unidades: cabe ao gerador selecionar a evidência certa. Por isso QA07 também exige answered. Não se incluiu ID de relevância no arquivo de perguntas nem se transformou a conferência pontual em métrica de recuperação.

QA10 e QA17 continuam condicionais, com expected_answerable=null e os dois status permitidos. Em QA10, responder exige fonte sobre o desfecho; uma troca apenas solicitada não comprova conclusão. Em QA17, answered só é aceitável se preservar explicitamente que a causa comprovada não foi observada e que hipóteses do cliente são hipóteses. Nos treze casos restantes, expected_answerable=false e o status esperado é abstained.

status_matches_expected significa somente compatibilidade formal com a expectativa de status. Não é uma nota de qualidade, não valida fontes e não aprova conteúdo. Uma saída answered sem suporte ou irrelevante falha mesmo que o status seja permitido. Um sistema que recusa tudo falha nos nove casos positivos; não pode ser divulgado como 24/24 aprovado. A revisão definitiva deve confrontar cada resposta com sources.context_text; não é um julgamento automático feito por outro modelo nem uma avaliação humana.

Os casos de contagem, percentual e ranking requerem abstained nesta versão: o pipeline avaliado não realiza classificação global nem agregação geográfica validada. Caso uma versão futura implemente esses recursos, revisar e versionar as expectativas antes da próxima execução, sem reinterpretar retroativamente o resultado deste lote.

## Execução reproduzível

1. Congelar estes arquivos e a configuração antes do lote. Registrar hash do conjunto, commit/código, modelo e revisão, modo de recuperação, limiar, top-k, número mínimo de fontes e manifesto do índice.
2. Enviar question e filters de cada caso sem editar a pergunta após ver a resposta. Não fornecer expectation, allowed_statuses ou expected_answerable ao gerador: são informações do avaliador. O contrato positivo do gerador, se existente, deve ser registrado separadamente; não copiar a resposta esperada da rubrica.
3. Salvar resposta completa, response_contract, status, motivo, findings, illustrative_quotes, context_evidence_ids, sources.context_text, metadados, tempo, configuração, literal_quotes_verified e summary_entailment_verified. Se houver erro técnico, registrá-lo como erro; não convertê-lo em abstenção correta.
4. Avaliar todas as respostas, incluindo recusas e saídas vazias. Não selecionar apenas exemplos bem-sucedidos para o relatório.
5. Se ajustar prompt, guardas ou parâmetros com base no lote, tratá-lo como conjunto de desenvolvimento observado. Separar os resultados anteriores dos posteriores; não anunciar a repetição como teste cego ou estimativa independente.

## Contrato de apresentação avaliado

Em context-synthesis-v2, findings contém sínteses sem IDs por afirmação. context_evidence_ids identifica todas as avaliações efetivamente enviadas como contexto, no nível da resposta. illustrative_quotes contém exemplos com seus IDs e origem literal conferida. Os exemplos não são apresentados como prova individual de cada frase da síntese. literal_quotes_verified=true não equivale a summary_entailment_verified=true; este último permanece false, pois o sistema não certifica automaticamente o suporte semântico da paráfrase.

A revisão deve confrontar cada finding com TODO o sources.context_text e os metadados disponibilizados ao gerador. Uma síntese pode ser sustentada por uma avaliação do contexto que não foi escolhida como exemplo ilustrativo. Não reprovar esse caso por exigir retroativamente citação atômica que o contrato atual não promete. Por outro lado, listar todo o contexto não justifica uma proposição que nenhuma fonte sustenta: conteúdo inventado, desfecho ainda pendente transformado em concluído ou causa não observada continuam falhas.

Avaliar separadamente a pertinência dos exemplos ilustrativos. Um exemplo pode ter origem literal correta e ser fraco ou irrelevante para a pergunta, sem que isso prove ou refute sozinho toda a síntese. Registrar a limitação específica. Findings devem ser uma síntese em terceira pessoa; comentários copiados em primeira pessoa pertencem aos exemplos, não substituem uma interpretação útil.

Os snapshots antigos com claims/evidence_ids por afirmação e realinhamento automático de citações pertencem a contratos anteriores. Preservar seus relatórios e conclusões históricas, sem misturar suas métricas com esta execução. No contrato atual, a identificação de uma fonte de apoio pelo revisor é uma anotação técnica assistida por IA, não uma garantia atômica produzida pelo aplicativo.

## Rubrica por finding e por resposta

| Dimensão | 2: adequada | 1: parcial | 0: falha |
|---|---|---|---|
| Suporte no contexto | O contexto efetivamente enviado sustenta o conteúdo e seu grau de certeza | Sustenta só parte ou o enquadramento perde uma ressalva | Nenhuma fonte do contexto sustenta o conteúdo ou a informação não foi fornecida |
| Pertinência à pergunta | Responde ao tema e ao recorte solicitado | Mistura conteúdo útil com material lateral | Tema oposto, irrelevante ou resposta a outra pergunta |
| Escopo e incerteza | Distingue relato/opinião, metadado e fato comprovado | Faz generalização ambígua ou atribuição pouco clara | Transforma hipótese em causa confirmada ou amostra em estatística global |
| Cobertura e síntese | Seleciona o essencial, agrupa o tema quando pertinente e responde ao pedido | Extratos corretos, mas redundantes ou com cobertura limitada | Copia fontes sem seleção, ignora o pedido ou inventa conclusão para preencher lacunas |
| Filtros e rastreabilidade | Todas as fontes cumprem os filtros, os IDs globais correspondem ao contexto usado e os exemplos têm origem literal correta | Apresentação incompleta ou exemplo pouco pertinente, sem contradição material | Desrespeita filtro, troca origem de exemplo ou usa contexto que não foi fornecido |

Para cada finding, registrar suporte como yes/no/partial e pertinência como yes/no/partial, além da razão e dos IDs do contexto identificados pelo revisor como apoio. Essa anotação não altera as referências da saída do aplicativo. Para cada exemplo ilustrativo, registrar origem literal e pertinência separadamente. A escala 0–2 da tabela ajuda a discutir a resposta inteira; não há necessidade de inventar uma precisão numérica a partir dela. Dimensões não aplicáveis a uma recusa correta recebem N/A. Em um caso positivo recusado sem necessidade, marcar utilidade/abstenção como falha; N/A não pode apagar essa falha.

Uma citação literal validada demonstra coincidência textual. Não demonstra automaticamente pertinência, verdade de uma opinião, exatidão causal, frequência populacional ou suporte integral do finding. O contrato atual não realinha automaticamente IDs de paráfrases e não declara que os exemplos provam toda a síntese. Cobrança dupla requer evidência do evento de pagamento; unidades repetidas ou produto duplicado são temas diferentes.

Para respostas recusadas, verificar: a pergunta era externa, o recorte estava vazio, as fontes eram insuficientes, a causa/estatística não era observável ou faltava esclarecimento? Uma recusa necessária é correta; uma recusa de pergunta respondível com contexto suficiente é falha de utilidade. Nos nove positivos, se uma versão futura da recuperação deixar de trazer a evidência disponível, registrar a lacuna de recuperação e a ausência de resposta, sem converter isso em sucesso de ponta a ponta. Em pergunta ambígua, um pedido claro de esclarecimento é apropriado e pode ser representado por abstained.

## Relato dos resultados

Apresentar resultados por grupo, com contagens de respostas, recusas necessárias, recusas desnecessárias, erros técnicos e falhas de suporte/pertinência. Apresentar a cobertura dos nove positivos separadamente do acerto das treze recusas obrigatórias e da revisão dos dois condicionais. Não chamar status_matches_expected de acurácia ou qualidade. Relatar separadamente suporte das sínteses no contexto completo, pertinência dos exemplos, erros de formato/origem literal rejeitados e falhas que permaneceram na saída final. Somente os contratos antigos registram IDs automaticamente realinhados; não transferir essa medida para o contrato atual. Não somar uma execução repetida da mesma pergunta como caso independente.

Identificar o avaliador como revisão assistida por IA. Não chamar este processo de avaliação humana. Uma avaliação humana futura, se realizada, deve ter registro próprio. Não afirmar que estes 24 casos comprovam segurança geral, causalidade, estatísticas do corpus ou qualidade equivalente entre modelos.
