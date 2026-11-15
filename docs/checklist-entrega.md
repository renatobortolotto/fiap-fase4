# Checklist de entrega

Os itens marcados foram verificados na implementação local; os demais dependem de revisão da equipe, publicação ou gravação. Consulte reports/verificacao.md para o ambiente e os limites. O prazo de entrega deve ser confirmado no ambiente da disciplina: o PDF não informa uma data.

## Solução

- [ ] Dataset Olist obtido da fonte indicada, com versão/data e hashes registrados.
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

## Avaliação

- [x] Testes de software executados, com resultado e ambiente registrados.
- [ ] Perguntas de desenvolvimento separadas das perguntas de avaliação final.
- [ ] Avaliações relevantes rotuladas por pessoas para um conjunto de perguntas.
- [ ] Rótulos propostos por IA no pool de desenvolvimento revisados e identificados como tal.
- [ ] Métricas de recuperação calculadas somente onde há rótulos válidos.
- [ ] Citações e sustentação semântica revisadas por pessoas.
- [ ] Erros de abstenção e de respostas sem suporte registrados.
- [x] Limiar inicial distinguido de um limiar calibrado.
- [x] Melhora da busca híbrida no pool de desenvolvimento distinguida de um teste final independente.
- [ ] Limitações e pendências refletidas no README e no vídeo.

## Repositório público no GitHub

- [x] Código-fonte e arquivo de dependências incluídos.
- [x] README explica problema, instalação, execução e configuração.
- [x] Arquitetura e principais decisões técnicas descritas.
- [x] Preparação do corpus e pipeline RAG documentados.
- [x] Exemplos de perguntas e respostas reais, com fontes, incluídos.
- [ ] Comandos conferidos em um ambiente limpo.
- [x] Arquivos temporários, caches e pesos de modelos fora do versionamento.
- [x] Segredos e credenciais fora do versionamento.
- [x] Condições de uso e atribuição do dataset verificadas na fonte.
- [ ] Link público abre para um visitante sem acesso à conta da equipe.

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
