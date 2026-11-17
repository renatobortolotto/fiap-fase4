# Revisão assistida das respostas nativas 7B — v4

**Os critérios materiais dos 24 casos técnicos observados foram atendidos, com ressalvas de qualidade.** Os nove positivos responderam com suporte no contexto completo; as treze recusas obrigatórias e os dois condicionais foram adequados. Não se observaram os erros materiais das versões anteriores.

Esta conclusão resulta de revisão assistida por IA de cada síntese contra todas as fontes fornecidas e da análise separada dos exemplos. Um segundo agente fez o contraponto dos nove positivos. Não é avaliação humana, benchmark cego, avaliação de população ou prova semântica automática.

Artefato: `native-acceptance-v4.json`; SHA-256 `e0c978c45d76fc55a8193a2b1c51bf19817335e6d714ac6f0ba68b6dea70d4f1`. Perguntas: `66e60d1f3f721b52b178d4b4228b3d4a68d05bbaff4d0680018d205bab47723d`. Modelo `Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M`, revisão `bb5d59e06d9551d752d08b292a50eb208b07ab1f`. Commit declarado pelo controlador: `1bcc442`. Contrato: `context-synthesis-v2`.

## Resultado por caso

| Caso | Status | Revisão do conteúdo |
|---|---|---|
| QA01 | answered | Adequado com ressalva de qualidade |
| QA02 | answered | Adequado com ressalva de qualidade |
| QA03 | answered | Adequado com ressalva de qualidade |
| QA04 | answered | Adequado neste caso observado |
| QA05 | answered | Adequado com ressalva de qualidade |
| QA06 | answered | Adequado neste caso observado |
| QA07 | answered | Adequado neste caso observado |
| QA08 | answered | Adequado com ressalva de qualidade |
| QA09 | answered | Adequado com ressalva de qualidade |
| QA10 | abstained | Recusa necessária adequada |
| QA11 | abstained | Recusa necessária adequada |
| QA12 | abstained | Recusa necessária adequada |
| QA13 | abstained | Recusa necessária adequada |
| QA14 | abstained | Recusa necessária adequada |
| QA15 | abstained | Recusa necessária adequada |
| QA16 | abstained | Recusa necessária adequada |
| QA17 | abstained | Recusa necessária adequada |
| QA18 | abstained | Recusa necessária adequada |
| QA19 | abstained | Recusa necessária adequada |
| QA20 | abstained | Recusa necessária adequada |
| QA21 | abstained | Recusa necessária adequada |
| QA22 | abstained | Recusa necessária adequada |
| QA23 | abstained | Recusa necessária adequada |
| QA24 | abstained | Recusa necessária adequada |

## Suporte, filtros e limites observados

Os dez findings publicados têm suporte no contexto completo. Nove são diretamente pertinentes; a segunda frase de QA02 inclui pontualidade, lateral à pergunta sobre características do produto, junto da apresentação do produto que é pertinente. Os 12 exemplos têm origem literal normalizada válida; um exemplo genérico de QA01 é pouco pertinente aos motivos concretos. Não se observaram violações dos filtros nem cópia de comentários em primeira pessoa como síntese.

QA03 e QA05 continuam pouco específicos. Em QA05, as fontes também não identificam a característica exata divergente; explicitar esse limite seria mais útil que somente afirmar a diferença. QA08 usa como exemplo um relato de não entrega; a ausência de nota fiscal é sustentada por outra fonte do contexto, o que é compatível com exemplos ilustrativos sem promessa de prova por frase. Em QA09, Estou na espera é pertinente, mas um trecho com o prazo ultrapassado ilustraria melhor a síntese; na data da avaliação marcaria melhor a pendência histórica.

Essas são ressalvas de cobertura/apresentação. Não foram observados nesta execução números de duração inventados, hipóteses operacionais apresentadas como comprovadas, desfechos não observados ou frequência populacional inferida da amostra. Isso não demonstra que tais erros sejam impossíveis em outras perguntas.

## Evolução de desenvolvimento preservada

- **v1:** QA09 inventou seis meses, corretamente bloqueados, mas ficou sem resposta; QA17 inferiu problema interno não comprovado.
- **v2:** corrigiu esses dois casos, mas QA10 converteu ausência de informação sobre o desfecho em falta de atendimento.
- **v3:** corrigiu QA10, mas QA01 acrescentou a prevalência comuns sem método.
- **v4:** esses acréscimos não aparecem. Os relatórios e saídas anteriores permanecem preservados, sem aprovação retroativa.

## Demonstrações e comparação de contexto

As duas respostas de demonstração em demo-context-v2 foram revisadas separadamente: atraso/comunicação e elogios de entrega em 2017 têm suporte no contexto e exemplos literais. As recusas de contagem global e período 2040 são adequadas. No exemplo de elogios, E1 é um relato misto: elogia esta entrega e reclama de outra, portanto é uma ilustração menos clara que E2, sem invalidar a síntese limitada às experiências positivas. Esses quatro casos não aumentam o denominador dos 24.

As demonstrações foram geradas no código c825981, antes do último controle de frequência, e não são apresentadas como novas gerações do código 1bcc442. Seu conteúdo examinado não anuncia prevalência.

A comparação registrada em `cold-context-comparison.json` (SHA-256 `0f55c87cafa30928f29c26e77a1ba46b0d0d15befe7ad5dd04c7fe2db8e877ac`) informa igualdade de contexto ordenado, escopo e filtros nos 24 casos após reconstruir o índice. Essa comparação não gerou novas respostas e não constitui outra nota semântica.

## Conclusão delimitada

**24/24 significa compatibilidade formal de status, não qualidade universal.** A leitura assistida das fontes sustenta que os critérios materiais deste conjunto observado foram cumpridos, com as limitações descritas. Os exemplos literais verificam origem; summary_entailment_verified permanece false. Os testes foram observados durante o desenvolvimento e não substituem avaliação humana futura nem um conjunto independente.
