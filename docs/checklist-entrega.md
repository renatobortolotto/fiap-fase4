# Checklist de entrega

Esta lista distingue a preparação técnica, a gravação e a submissão. Os controles de testes e revisão detalhada complementam o enunciado; um benchmark humano independente não é um pré-requisito declarado no PDF. Consulte [a verificação](../reports/verificacao.md) para resultados e limites. Confirme o prazo no ambiente da disciplina: o PDF não informa uma data.

## Solução

- [x] Dataset Olist obtido da fonte indicada, com versão/data e hashes registrados; ZIP local conferido.
- [x] Preparação executada com resumo real de entradas, descartes e documentos.
- [x] Ausentes e duplicatas tratados com critérios documentados.
- [x] Unidade do documento e relacionamento com pedido preservados.
- [x] Embeddings semânticos criados e índice persistido.
- [x] Configuração do modelo e integridade do índice conferidas.
- [x] Consulta com LLM retorna resposta e avaliações identificáveis.
- [x] Fontes exibidas correspondem aos documentos enviados ao modelo.
- [x] Rótulos E1/E2 de cada resposta mapeiam aos `doc_id` estáveis na exportação.
- [x] Pergunta fora do escopo e recuperação insuficiente demonstram abstenção.
- [x] Filtros opcionais não retornam documentos fora do recorte.
- [x] Interface indica quando está apenas no modo de evidências.
- [x] Limites de frequência, causalidade e representatividade estão explícitos.

## Revisão técnica da versão atual

- [x] Testes de software executados, com resultado e ambiente registrados.
- [x] Lote de 24 consultas executado e sínteses confrontadas com o contexto completo, por revisão assistida por IA, com ressalvas registradas.
- [x] Rótulos do pool identificados como propostas de IA, sem alegação de revisão humana concluída.
- [x] Métricas de recuperação limitadas ao pool rotulado de desenvolvimento, com sua proveniência explícita.
- [x] Falhas encontradas e resultado após correções registrados, sem reescrever as saídas anteriores.
- [x] Limiar inicial distinguido de um limiar calibrado.
- [x] Melhora da busca híbrida no pool de desenvolvimento distinguida de um teste final independente.
- [x] README e relatórios refletem o estado final da revisão; levar esses limites para o vídeo.

## Repositório público no GitHub

- [x] Código-fonte e arquivo de dependências incluídos.
- [x] README explica problema, instalação, execução e configuração.
- [x] Arquitetura e principais decisões técnicas descritas.
- [x] Preparação do corpus e pipeline RAG documentados.
- [x] Exemplos de perguntas e respostas reais, com fontes, incluídos.
- [x] Instalação uv e ZIP local conferidos em clone/venv/cache de modelos novos, com testes, conversa nativa via AppTest e payload de exportação.
- [x] Arquivos temporários, caches e pesos de modelos fora do versionamento.
- [x] Segredos e credenciais fora do versionamento.
- [x] Condições de uso e atribuição do dataset verificadas na fonte.
- [x] Link público abre para um visitante sem acesso à conta da equipe.

## Melhorias futuras de avaliação

Um teste cego separado, rótulos humanos de relevância, conciliação entre avaliadores e calibração independente do limiar ampliariam a evidência de qualidade. Essas atividades não foram executadas nem são apresentadas como requisitos adicionais da entrega. Os ensaios atuais são de desenvolvimento observado e não provam ausência geral de alucinações.

## Vídeo

- [ ] Duração final não supera 7 minutos.
- [ ] Problema de negócio e arquitetura explicados.
- [ ] Preparação, recuperação e construção do contexto demonstradas.
- [ ] Exemplo com evidências, exemplo com filtro e exemplo de abstenção gravados.
- [ ] Desafios, decisões e resultados reais apresentados.
- [ ] Áudio, legibilidade e permissão do link conferidos.
- [ ] Integrantes e links de entrega identificados conforme a orientação da disciplina.

## Conferência acadêmica

- [ ] Prazo e local de submissão confirmados no ambiente da disciplina.
- [ ] Trabalho revisado pela equipe antes do envio.
- [ ] Repositório e vídeo submetidos nos campos solicitados.

A trilha Databricks citada no PDF é um incentivo adicional, não um componente obrigatório desta solução. Caso a equipe busque o bônus, conferir as regras vigentes da disciplina e apresentar um comprovante identificável de conclusão. Não marcar a solução como incompleta apenas por não realizar essa trilha.
