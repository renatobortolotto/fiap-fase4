# Roteiro do vídeo - 6 minutos e 50 segundos

Este é um roteiro de gravação, não um registro de resultados. Use saídas reais do contrato `context-synthesis-v2` e apresente falhas ou limitações observadas. Os números finais de testes, aceitação e instalação limpa desta revisão ainda estão pendentes: não anunciá-los como concluídos no vídeo antes de conferir os relatórios.

## Preparação antes da gravação

- Obter a base Olist, preparar os documentos e construir o índice.
- Conferir o `.env`: o padrão é Qwen2.5-7B-Instruct-GGUF Q4_K_M com runtime portátil gerenciado, em CPU. Executar `python -m voc_olist models` antes da gravação para obter os arquivos. Transformers 1,5B e Ollama são alternativas opcionais.
- Executar previamente as três consultas abaixo, conferir fontes e ajustar o recorte somente com justificativa.
- Manter prontos o diagrama e um relatório real desta revisão, identificado por modelo e contrato. Não apresentar relatórios históricos como nova validação.
- Identificar o grupo, o link do repositório e o equipamento usado.
- Ensaiar e verificar o tempo do arquivo exportado; o limite do desafio é 7 minutos.

## 0:00-0:40 - Problema de negócio

“Gestores recebem muitas avaliações e precisam entender o que os clientes relatam. Construímos uma solução de Voice of Customer sobre comentários da Olist. Recuperamos relatos relacionados à pergunta e o modelo sintetiza o contexto consultado, mostrando também trechos ilustrativos com origem conferida.”

Explicar que a base é histórica e que os relatos recuperados não permitem calcular frequência populacional. Um trecho ilustrativo não certifica toda a síntese.

## 0:40-1:30 - Base e preparação

Mostrar o arquivo de avaliações e o resumo real de preparação. Explicar a união entre título e comentário, o tratamento de ausentes, os identificadores preservados e os metadados opcionais. Mostrar que pedidos com vários itens não multiplicam artificialmente a mesma avaliação. A codificação reaproveita vetores de textos iguais, mas preserva cada documento e seus metadados.

## 1:30-2:20 - Arquitetura e decisões

Mostrar o diagrama de `arquitetura.md`. Percorrer guard de escopo e período, filtros, busca densa, reordenação BM25/RRF, contexto completo e LLM local. Explicar que BM25 só reordena candidatos densos elegíveis. O padrão usa Qwen 7B quantizado e um llama.cpp portátil iniciado e encerrado pela própria aplicação em loopback. Dizer: “Usamos schema JSON e conferimos a origem dos exemplos. Esses controles não certificam a interpretação; a síntese ainda precisa ser avaliada contra todo o contexto.”

## 2:20-3:30 - Demonstração 1: reclamações de entrega

Pergunta: **“O que os clientes relatam sobre problemas relacionados à entrega?”**

Selecionar notas 1 e 2 e tornar esse recorte visível. Executar com o provedor nativo configurado. Ler a síntese e mostrar **Contexto consultado**, com o conjunto de fontes enviado ao modelo. Abrir **Trechos ilustrativos** e mostrar que cada exemplo corresponde ao texto da fonte indicada. Em **Avaliações recuperadas**, inspecionar os relatos relevantes e, no JSON, o `doc_id` persistente.

Explicar: “A síntese considera o contexto completo; os exemplos são ilustrativos, não uma atribuição de prova para cada frase.” Se houver recusa ou falha, apresentar o motivo real sem editar uma resposta substituta.

Não dizer que um tema é “o mais frequente da Olist” a partir dessa seleção.

## 3:30-4:30 - Demonstração 2: experiências positivas

Pergunta: **“Quais experiências positivas são descritas sobre a entrega em 2017?”**

Limpar o filtro anterior e selecionar notas 4 e 5 explicitamente. Mostrar o ano identificado na pergunta, o período efetivo e as datas das fontes. Explicar que nota e categoria continuam sendo filtros manuais. Abrir o contexto e os exemplos e exportar o JSON com `inferred_period`, filtros efetivos e `context_evidence_ids`. Verificar a síntese contra os relatos, preservando opiniões e hipóteses como tais.

## 4:30-5:15 - Demonstração 3: pergunta sem suporte

Pergunta: **“Quantos clientes reclamaram de atraso em toda a base?”**

Mostrar a recusa da agregação e explicar que a busca por relevância não calcula contagens globais de temas. O gestor pode reformular para investigar relatos. Mencionar períodos sem dados e tarefas externas como outras situações de recusa. O `ScopeGuard` é uma heurística; não garante identificar todos os casos, e o modelo também deve se abster quando o tema não é sustentado.

## 5:15-6:15 - Avaliação e limites

Mostrar somente um relatório efetivamente produzido para esta revisão. Separar os controles:

1. Testes de software verificam preparação, integridade, filtros e contrato.
2. JSON restrito controla formato, e correspondência literal confere origem dos exemplos.
3. Leitura da síntese contra o contexto completo avalia sustentação semântica.

Se o ensaio de aceitação assistido por IA já tiver sido concluído, identificá-lo como desenvolvimento e explicar que ele aguarda leitura do revisor; não chamá-lo de avaliação humana ou benchmark independente. Se ainda não tiver terminado, informar a pendência. Mostrar `literal_quotes_verified` e `summary_entailment_verified` no JSON e esclarecer seus significados distintos. Não anunciar uma taxa de “respostas verdadeiras” nem conclusões estatísticas a partir das demonstrações.

## 6:15-6:50 - Reprodutibilidade e encerramento

Mostrar o README, `Setup.ps1 -ArchivePath` para o ZIP e `python -m voc_olist models` para preparar modelos e runtime. Explicar que a configuração recomenda 16 GB de RAM e cerca de 10 GB livres, preserva `.env` e não exige instalação global do llama.cpp. Declarar o estado real dos pilotos, da aceitação e da instalação limpa, sem anunciar validação antes de conferir as execuções. Encerrar com o valor da solução: investigação qualitativa com síntese, contexto disponível para revisão e exemplos rastreáveis.

## Conferência do arquivo final

- Duração de até 7 minutos, com áudio e textos legíveis.
- Links acessíveis ao avaliador.
- Demonstração com LLM identificada; modo de trechos não apresentado como RAG completo.
- Resultados apresentados correspondem às execuções gravadas.
- Contexto global e exemplos ilustrativos apresentados com significados distintos.
- Nenhuma conferência literal ou restrição de formato apresentada como certificação semântica.
- Nenhuma credencial, token ou informação pessoal desnecessária aparece na tela.
