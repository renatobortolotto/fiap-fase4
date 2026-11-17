# Revisão assistida das respostas nativas 7B — v2

**O lote v2 ainda não cumpriu a aceitação material.** Os nove positivos foram respondidos e as treze recusas obrigatórias foram adequadas. QA09 e QA17 foram corrigidos, mas QA10 publicou uma inferência indevida sobre ausência de atendimento.

Revisão assistida por IA das 24 respostas contra o contexto integral, com contraponto de um segundo agente para os nove positivos. Não é avaliação humana, benchmark cego, julgamento automático de outro modelo ou prova semântica automática.

Artefato: `native-acceptance-v2.json`; SHA-256 `2aa43d89c824b74c2bd4203b50f89d07ca8058733ec455107094f32dff2efbf3`. Perguntas: `66e60d1f3f721b52b178d4b4228b3d4a68d05bbaff4d0680018d205bab47723d`. Modelo `Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M`, revisão `bb5d59e06d9551d752d08b292a50eb208b07ab1f`. Commit declarado pelo controlador: `b1d9f2f`.

## Falha material de QA10

> Muitos clientes que pediram troca ou devolução não receberam resposta sobre como o problema foi resolvido.

Somente E6 afirma falta de retorno. E2 diz que recebeu um retorno e aguarda outro email. Os demais comentários registram intenção ou solicitação, sem informar atendimento ou desfecho. **Ausência de informação sobre o resultado não comprova ausência de resposta recebida.** O quantificador muitos amplia uma condição não demonstrada. A origem literal do exemplo E2 é correta, mas isso não valida essa interpretação.

## Correções observadas

- **QA09:** respondeu sobre espera após o prazo sem inventar seis meses ou outra duração. As oito fontes cumprem o período de compra e o filtro de atraso.
- **QA17:** recusou a causa comprovada e explicou que as avaliações são percepções, não comprovação operacional.

## Resultado por caso

| Caso | Status | Revisão do conteúdo |
|---|---|---|
| QA01 | answered | Adequado com ressalva de qualidade |
| QA02 | answered | Adequado neste caso observado |
| QA03 | answered | Adequado com ressalva de qualidade |
| QA04 | answered | Adequado neste caso observado |
| QA05 | answered | Adequado com ressalva de qualidade |
| QA06 | answered | Adequado com ressalva de qualidade |
| QA07 | answered | Adequado neste caso observado |
| QA08 | answered | Adequado com ressalva de qualidade |
| QA09 | answered | Adequado com ressalva de qualidade |
| QA10 | answered | Falha material: infere falta de resposta sem suporte suficiente |
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

## Notas de qualidade e limites

Dos 11 findings publicados, dez têm suporte e um tem suporte parcial pelo erro de QA10. Os 14 exemplos têm origem literal normalizada válida; um exemplo de QA01 é pouco pertinente por expressar insatisfação genérica. Não foram observadas violações dos filtros ou cópia de comentários em primeira pessoa como findings.

QA03 e QA05 são genéricos; QA05 não inventa características que as fontes não informam, mas poderia explicitar essa limitação. QA08 usa notas fiscais ruins de forma vaga, com apoio no relato de nota colada/rasgada e nota ausente. QA09 poderia marcar melhor o tempo histórico com na data da avaliação e usar um exemplo que inclua o prazo ultrapassado. Essas são ressalvas de qualidade, distintas da falha material de QA10.

**24/24 é apenas compatibilidade de status, não uma nota de qualidade.** A v2 fica preservada como execução de desenvolvimento não aprovada materialmente. A revisão de uma futura v3 deve considerar todas as respostas, sem antecipar aprovação nem sobrescrever os resultados anteriores.
