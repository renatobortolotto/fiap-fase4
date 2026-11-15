# Roteiro do vídeo - 6 minutos e 50 segundos

Este é um roteiro de gravação, não um registro de resultados. Substitua as referências a respostas pelos comportamentos realmente observados. Se houver uma limitação ou falha na execução, apresente-a com clareza.

## Preparação antes da gravação

- Obter a base Olist, preparar os documentos e construir o índice.
- Conferir o `.env`: iniciar Ollama se esse for o provedor, ou carregar o modelo Transformers configurado. Abrir a aplicação Streamlit.
- Executar previamente as três consultas abaixo, conferir fontes e ajustar o recorte somente com justificativa.
- Manter prontos o diagrama de arquitetura e um relatório de execução real.
- Identificar o grupo, o link do repositório e o equipamento usado.
- Ensaiar e verificar o tempo do arquivo exportado; o limite do desafio é 7 minutos.

## 0:00-0:40 - Problema de negócio

“Gestores recebem muitas avaliações e precisam entender o que os clientes relatam, com acesso às evidências. Construímos uma solução de Voice of Customer sobre comentários do dataset Olist. Uma pessoa faz uma pergunta, recuperamos relatos relacionados e o modelo produz uma resposta vinculada às fontes.”

Explicar que a base é histórica e que esta aplicação explora relatos, sem transformar top-k em estatística de toda a base.

## 0:40-1:30 - Base e preparação

Mostrar o arquivo de avaliações e o resumo de preparação produzido na execução. Informar as quantidades reais: linhas de entrada, textos vazios descartados e documentos finais. Explicar a união entre título e comentário, os identificadores preservados e os metadados opcionais. Mostrar que pedidos com vários itens não multiplicam artificialmente a mesma avaliação.

## 1:30-2:20 - Arquitetura e decisões

Mostrar o diagrama de `arquitetura.md`. Percorrer embeddings, persistência, recuperação, contexto, LLM e validação das citações. Explicar: “Após observar erros de especificidade na linha de base, acrescentamos uma reordenação BM25 combinada por RRF aos candidatos da busca densa. Esse ajuste melhorou as métricas no nosso pool de desenvolvimento; ainda precisa de validação humana e teste separado.” Indicar que os filtros e o limiar de cosseno valem antes da reordenação, e que BM25 não recupera fora desse pool. Declarar que o limiar inicial é uma configuração a validar.

## 2:20-3:30 - Demonstração 1: reclamações de entrega

Pergunta: **“O que os clientes relatam sobre problemas relacionados à entrega?”**

Selecionar notas 1 e 2 e tornar esse recorte visível. Executar em modo com LLM. Ler uma afirmação e abrir os comentários citados. Mostrar rótulos E1/E2, nota e texto de pelo menos duas fontes; na exportação, indicar o `doc_id` estável associado. Conferir se os relatos sustentam a afirmação. Se o sistema se abstiver, explicar o motivo observado e demonstrar a inspeção da recuperação.

Não dizer que um tema é “o mais frequente da Olist” a partir dessa seleção.

## 3:30-4:30 - Demonstração 2: experiências positivas

Pergunta: **“Quais aspectos da experiência de compra aparecem nos elogios?”**

Limpar o filtro anterior e selecionar notas 4 e 5. Mostrar o efeito do recorte nas fontes e abrir os comentários usados. Explicar por que disponibilizar o texto original ajuda o gestor a verificar a interpretação. Exportar o resultado em JSON para ilustrar a rastreabilidade.

## 4:30-5:15 - Demonstração 3: pergunta sem suporte

Pergunta: **“Qual será o faturamento da empresa em 2027?”**

Mostrar a abstenção e explicar que avaliações históricas não sustentam essa previsão. Mencionar também o caso de filtros que não retornam documentos: o sistema deve comunicar a limitação, sem preencher a lacuna com uma resposta plausível.

## 5:15-6:15 - Avaliação e limites

Mostrar o relatório efetivamente produzido. Separar três evidências:

1. Testes de software verificam preparação, integridade, filtros e contrato de fontes.
2. Consultas executadas demonstram o funcionamento naquele ambiente.
3. Julgamentos humanos de relevância e sustentação medem a qualidade do RAG.

Se mostrar o pool incluído de 17 avaliações e cinco perguntas, identificar seus rótulos como propostos com auxílio de IA e pendentes de revisão humana. Mostrar Recall@4 de 0,5625 para 0,675 e MRR@4 de 0,875 para 1,0, da busca densa para a híbrida. Explicar que o ajuste foi feito após observar esse mesmo pool, portanto seus resultados são de desenvolvimento e não comprovam qualidade no corpus principal. O gate acertou 5/5 casos em ambos, mas isso só mede quantidade de hits. Se ainda não houver avaliação humana, dizer isso e apresentar o protocolo pendente. Explicar que validar IDs não garante que a afirmação está correta, e que um modelo pequeno tem limitações.

## 6:15-6:50 - Reprodutibilidade e encerramento

Mostrar o README, os comandos e os documentos técnicos no repositório. Indicar os requisitos para executar, os modelos usados e as pendências conhecidas. Encerrar com o valor da solução: perguntas em linguagem natural, comentários recuperados e conclusões que podem ser conferidas nas fontes.

## Conferência do arquivo final

- Duração de até 7 minutos, com áudio e textos legíveis.
- Links acessíveis ao avaliador.
- Demonstração com LLM identificada; modo de trechos não apresentado como RAG completo.
- Resultados apresentados correspondem às execuções gravadas.
- Nenhuma credencial, token ou informação pessoal desnecessária aparece na tela.
