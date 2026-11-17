# Revisão assistida das respostas nativas 7B — v3

**O lote v3 ainda contém uma falha de escopo em QA01.** Os nove positivos responderam, as treze recusas obrigatórias foram adequadas e os dois condicionais foram tratados corretamente. Os erros materiais anteriores de duração, causa e desfecho não se repetiram.

Revisão assistida por IA das 24 respostas contra o contexto integral, com contraponto de um segundo agente nos nove positivos. Não é avaliação humana, benchmark cego nem prova semântica automática.

Artefato: `native-acceptance-v3.json`; SHA-256 `30696d037706b4abeb5b6f6c20316b32c507ec97a4e958b41221440808fec507`. Perguntas: `66e60d1f3f721b52b178d4b4228b3d4a68d05bbaff4d0680018d205bab47723d`. Modelo `Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M`, revisão `bb5d59e06d9551d752d08b292a50eb208b07ab1f`. Commit declarado pelo controlador: `c825981`.

## QA01: tema sustentado, prevalência não demonstrada

> O atraso na entrega e a falta de resposta do vendedor são insatisfações comuns entre os clientes que deram 1 ou 2 estrelas.

E3 sustenta atraso e falta de retorno. A palavra comuns acrescenta uma afirmação de frequência que não foi medida, e E3 é a única fonte explícita dessa combinação no contexto recuperado. O prefixo que delimita a resposta aos comentários recuperados reduz o alcance, mas não demonstra prevalência dentro ou fora desse conjunto.

O suporte foi classificado como parcial por esse acréscimo. É uma falha de gravidade menor que a duração ou causa inventadas nas versões anteriores, mas não apenas preferência estilística. Uma formulação de existência de relatos, sem o adjetivo de frequência, teria suporte.

## Resultados por caso

| Caso | Status | Revisão do conteúdo |
|---|---|---|
| QA01 | answered | Suporte parcial: frequência não demonstrada |
| QA02 | answered | Adequado neste caso observado |
| QA03 | answered | Adequado com ressalva de qualidade |
| QA04 | answered | Adequado neste caso observado |
| QA05 | answered | Adequado com ressalva de qualidade |
| QA06 | answered | Adequado com ressalva de qualidade |
| QA07 | answered | Adequado neste caso observado |
| QA08 | answered | Adequado neste caso observado |
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

## Rastreabilidade e qualidade

Dos dez findings publicados, nove têm suporte e um tem suporte parcial pela prevalência indevida. Os 13 exemplos têm origem literal normalizada válida; um exemplo genérico de QA01 é pouco pertinente aos motivos concretos. Não se observaram violações dos filtros nem cópia em primeira pessoa como finding.

QA04 acrescentou um exemplo de cadeira parcialmente montada e com peça faltando, sustentado por E8. QA08 melhorou a precisão ao mencionar produto errado, troca e emissão da nota conforme E3/E6/E8. QA03 e QA05 continuam genéricos; QA09 usa um exemplo curto que não ilustra por si só o prazo ultrapassado, embora o contexto integral o sustente. São limitações de cobertura/apresentação, distintas da falha de escopo de QA01.

**24/24 não é nota de qualidade.** Preservar esta execução observada e revisar a versão seguinte sem modificar retroativamente os resultados. Este relatório não declara validação semântica automática nem estima desempenho em perguntas não testadas.
