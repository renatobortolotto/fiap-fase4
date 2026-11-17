# Roteiro do vídeo - 6 minutos e 50 segundos

Este é um roteiro de gravação. Use os exemplos reais do contrato `context-synthesis-v2` em `reports/demo-detalhado/`, com parecer em `reports/review-20261116/focused-demo-source-review.md`. Há também registros da instalação fria, dos 288 testes e da aceitação assistida de 24 casos. Apresente o escopo e as ressalvas de cada evidência; o vídeo ainda precisa ser gravado.

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

Pergunta: **“Quais problemas concretos de entrega são descritos e o que aconteceu nesses casos?”**

Selecionar notas 1 e 2 e tornar esse recorte visível. Executar com o provedor nativo. Na execução registrada, a síntese menciona atrasos e falta de informações no rastreamento; o exemplo E1 relata não entrega e rastreamento sem informação. Mostrar **Contexto consultado**, **Trechos ilustrativos** e os relatos relevantes em **Avaliações recuperadas**, com `doc_id` persistente no JSON. A resposta é curta e não cobre todos os problemas disponíveis no contexto.

Explicar: “A síntese considera o contexto completo; os exemplos são ilustrativos, não uma atribuição de prova para cada frase.” Se houver recusa ou falha, apresentar o motivo real sem editar uma resposta substituta.

Não dizer que um tema é “o mais frequente da Olist” a partir dessa seleção.

## 3:30-4:30 - Demonstração 2: experiências positivas

Pergunta: **“Quais aspectos da entrega satisfizeram os compradores em 2017? Descreva exemplos concretos dos comentários.”**

Limpar o filtro anterior e selecionar notas 4 e 5 explicitamente. Mostrar o ano identificado, o período efetivo e as datas das fontes. A execução registrada sintetiza rapidez e satisfação, com o trecho E1 “Lindos produtos, rápida entrega. Recomendo.” Mostrar a origem desse exemplo e exportar o JSON com `inferred_period`, filtros e contexto. A interpretação automática cobre anos; meses e dias usam intervalo manual. A síntese continua curta, sem pretensão de análise abrangente.

## 4:30-5:15 - Demonstração 3: pergunta sem suporte

Pergunta: **“Quantos clientes reclamaram de atraso em toda a base?”**

Mostrar a recusa da agregação e explicar que a busca por relevância não calcula contagens globais de temas. O gestor pode reformular para investigar relatos. Mencionar períodos sem dados e tarefas externas como outras situações de recusa. O `ScopeGuard` é uma heurística; não garante identificar todos os casos, e o modelo também deve se abster quando o tema não é sustentado.

## 5:15-6:15 - Avaliação e limites

Mostrar somente um relatório efetivamente produzido para esta revisão. Separar os controles:

1. Testes de software verificam preparação, integridade, filtros e contrato.
2. JSON restrito controla formato, e correspondência literal confere origem dos exemplos.
3. Leitura da síntese contra o contexto completo avalia sustentação semântica.

Apresentar os 288 testes e o lote v4: nove respostas, treze recusas obrigatórias e dois condicionais também recusados. Explicar que a compatibilidade de status em 24/24 não é taxa de acurácia semântica. A leitura assistida por IA encontrou suporte nos dez findings desse lote e conferiu doze exemplos, com ressalvas de cobertura e pertinência; não é avaliação humana ou benchmark independente. Mostrar `literal_quotes_verified` e `summary_entailment_verified=false`. Mencionar que falhas anteriores foram preservadas e motivaram correções, sem alegar que novas consultas sejam livres de erro.

## 6:15-6:50 - Reprodutibilidade e encerramento

Mostrar o README e `Setup.ps1 -ArchivePath` para instalar e preparar o ZIP. Explicar a recomendação de 16 GB de RAM e 20 GB livres e a preservação de `.env`. A instalação uv foi concluída em clone novo, com modelos obtidos sem cache reaproveitado e conversa nativa offline via AppTest. O payload de exportação foi conferido, sem simular clique de navegador. Encerrar com o valor da solução: investigação qualitativa com síntese, contexto disponível para revisão e exemplos rastreáveis.

## Conferência do arquivo final

- Duração de até 7 minutos, com áudio e textos legíveis.
- Links acessíveis ao avaliador.
- Demonstração com LLM identificada; modo de trechos não apresentado como RAG completo.
- Resultados apresentados correspondem às execuções gravadas.
- Contexto global e exemplos ilustrativos apresentados com significados distintos.
- Nenhuma conferência literal ou restrição de formato apresentada como certificação semântica.
- Nenhuma credencial, token ou informação pessoal desnecessária aparece na tela.
