# Revisão assistida das respostas nativas 7B — v1

**O lote v1 não cumpriu a aceitação material.** Oito dos nove positivos foram respondidos; as 13 recusas obrigatórias foram adequadas. QA09 falhou em utilidade e QA17 publicou uma inferência causal não sustentada.

Esta é revisão assistida por IA das 24 respostas contra o contexto integral. Não é avaliação humana, benchmark cego, julgamento automático por outro modelo ou prova semântica automática. O JSON detalha cada finding, exemplo e verificação de filtro.

Artefato examinado: `native-acceptance-v1.json`; SHA-256 `6fff29a8a29a4c272851b52af4c5e1fcc24c5534f7b58707aab0577de2c5c1d3`. Perguntas: `66e60d1f3f721b52b178d4b4228b3d4a68d05bbaff4d0680018d205bab47723d`. Modelo: `Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M`, revisão `bb5d59e06d9551d752d08b292a50eb208b07ab1f`. Commit declarado pelo controlador: `641ee48`. Contrato: `context-synthesis-v2`.

## Achados materiais

- **QA09 — falha de geração e utilidade:** nenhuma fonte sustenta até 6 meses de atraso. O modelo repetiu essa duração nas duas tentativas e o gate a rejeitou corretamente. A informação não chegou à resposta final; entretanto, havia oito fontes para uma síntese útil e o caso terminou sem resposta.
- **QA17 — inferência causal publicada:** a falta de explicação é sustentada, mas problemas internos não resolvidos é hipótese do modelo. Sugerindo preserva alguma incerteza, porém não responde à causa comprovada e não declara que ela é desconhecida.

## Resultado por caso

| Caso | Status | Revisão do conteúdo |
|---|---|---|
| QA01 | answered | Adequado com ressalva de qualidade |
| QA02 | answered | Adequado com ressalva de qualidade |
| QA03 | answered | Adequado com ressalva de qualidade |
| QA04 | answered | Adequado neste caso observado |
| QA05 | answered | Adequado com ressalva de qualidade |
| QA06 | answered | Adequado com ressalva de qualidade |
| QA07 | answered | Adequado neste caso observado |
| QA08 | answered | Adequado com ressalva de qualidade |
| QA09 | abstained | Falha material de utilidade; invenção bloqueada |
| QA10 | answered | Adequado com ressalva de qualidade |
| QA11 | abstained | Recusa necessária adequada |
| QA12 | abstained | Recusa necessária adequada |
| QA13 | abstained | Recusa necessária adequada |
| QA14 | abstained | Recusa necessária adequada |
| QA15 | abstained | Recusa necessária adequada |
| QA16 | abstained | Recusa necessária adequada |
| QA17 | answered | Falha material de escopo causal |
| QA18 | abstained | Recusa necessária adequada |
| QA19 | abstained | Recusa necessária adequada |
| QA20 | abstained | Recusa necessária adequada |
| QA21 | abstained | Recusa necessária adequada |
| QA22 | abstained | Recusa necessária adequada |
| QA23 | abstained | Recusa necessária adequada |
| QA24 | abstained | Recusa necessária adequada |

## Qualidade e rastreabilidade

Os 12 findings publicados são em terceira pessoa: 11 têm suporte no contexto e 1 tem suporte parcial pelo acréscimo causal de QA17. Todos os 15 exemplos têm origem literal normalizada válida; 14 são pertinentes e 1 é parcialmente pertinente. Não foram observadas violações dos filtros. Esses números descrevem este lote observado, sem pretensão de estimativa populacional.

QA01 usa um exemplo de insatisfação genérica que não ilustra os motivos concretos, apesar de a síntese estar sustentada por outras fontes. QA02 e QA06 têm redundância; QA03 e QA05 são genéricos. QA08 usa português pouco natural ao resumir não entrega e problemas com notas fiscais, mas E5 descreve nota colada/rasgada e o contexto sustenta a interpretação sem confirmar fraude. QA10 preserva a ausência de desfecho, embora muitos clientes seja quantificador vago desnecessário.

O contexto global foi distinguido dos trechos ilustrativos: a origem literal dos exemplos não foi tratada como prova individual das frases. As fontes são relatos de clientes; nem a citação correta nem esta revisão comprovam eventos externos, causas operacionais ou satisfação de toda a população.

## Limites da conclusão

O registro 23/24 mede somente compatibilidade de status e não deve ser divulgado como taxa de qualidade. Preservar o lote v1 como evidência de desenvolvimento, sem sobrescrevê-lo. A versão corrigida precisa de uma nova execução e revisão completa; este relatório não a antecipa.
