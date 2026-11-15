# Observações de desenvolvimento

O primeiro ensaio foi feito no pool de 17 avaliações reais, com E5 sem reranking,
top-k 4 e limiar 0,75. Os rótulos foram propostos com auxílio de IA e ainda precisam
de revisão humana. Não se trata de um teste independente.

Nesse ensaio, a busca densa obteve Recall@4 0,5625 e MRR@4 0,875. A consulta sobre
atraso incluiu uma avaliação positiva de entrega antes do prazo. O cosseno alto
identificou proximidade do assunto entrega, mas não garantiu a relevância para a
pergunta específica. Esse resultado motivou a combinação de ranking semântico e
lexical. Comparações posteriores devem preservar o recorte e registrar o método.

`development-smoke.json` registra uma execução inicial com o modelo pequeno
Qwen2.5-0.5B-Instruct nesse pool. O JSON e as referências eram válidos, mas a resposta
incluiu comentários sobre avaria e entrega antecipada que não ajudavam a responder
à pergunta sobre atraso. Esse é um exemplo real de que validar referências não
comprova a pertinência das afirmações. Não usar essa saída como demonstração de
qualidade aprovada.

O prompt foi ajustado para solicitar até duas conclusões curtas, agrupar relatos e
ignorar fontes não pertinentes. O limite de geração do modelo pequeno foi reduzido
para evitar respostas excessivamente longas em CPU. Esses ajustes não substituem
a avaliação de sustentação semântica pela equipe.

No corpus completo, uma execução posterior do modelo pequeno copiou o texto de E3
e indicou E4. Isso motivou a conferência de trechos literais: o pós-processamento
agora usa correspondência textual para realinhar esse tipo específico de citação,
registrando os rótulos originais. Trechos literais aparecem como falas de clientes,
inclusive quando contêm opiniões ou suposições. Essa correção não verifica paráfrases.

Na comparação do mesmo pool de desenvolvimento, o reranking híbrido passou a
Recall@4 0,675 e MRR@4 1,0. O gate de recorte vazio teve 5/5 acertos nos casos
rotulados em ambos os métodos. O tema atraso continuou com Recall@4 0,5: a combinação
não resolveu toda confusão entre relatos sobre entrega. Os relatórios preservam os
IDs e scores para inspeção; os rótulos continuam pendentes de revisão humana.
