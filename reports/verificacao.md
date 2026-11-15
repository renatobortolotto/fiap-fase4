# Verificação da implementação local

Registro em UTC: 2026-11-15T21:55:03.048689+00:00. Projeto instalado em `raiz do repositório`.

## Ambiente e instalação

Ambiente virtual novo com Python 3.12.14, Windows e 6 CPUs lógicas.
Dependências instaladas com `uv sync --locked --extra dev`; modelos executados em CPU.
A configuração local `.env` usa Transformers com Qwen2.5-0.5B-Instruct, revisão fixada.
Ollama continua disponível como alternativa, mas seu servidor/modelo não foi executado nesta máquina.
O adaptador Ollama tem testes de contrato com respostas simuladas.

Versões verificadas: torch 2.15.0+cpu, transformers 5.23.0, sentence-transformers 6.3.0, numpy 2.5.4, streamlit 1.67.0, pytest 9.2.0.

## Dados e índice

99.224 avaliações oficiais de entrada, 56.537 sem texto excluídas, 42.687 documentos
finais; 1.737 documentos preservados com apenas título. Dados brutos e pesos ficam
fora do Git. O manifesto do download e o relatório de preparação registram hashes.

Índice com 42.687 × 384 valores float32, 65.567.232 bytes na matriz persistida.
Modelo E5 na revisão `614241f622f53c4eeff9890bdc4f31cfecc418b3`; integridade e normalização conferidas.
Execução final da indexação: 757,59 segundos, incluindo configurações restantes do modelo.

## Testes e interface

**107 testes passaram, zero falhas**, em 1,61 s na pasta definitiva, após a cópia final.
Comando: `.venv\Scripts\python.exe -m pytest -q --basetemp artifacts\pytest-final-02`.
Cobrem preparação, joins, ausentes, persistência, integridade, filtros, ranking,
BM25/RRF, referências inválidas, alinhamento de trechos literais, abstenção e interface.
Fixtures de software são sintéticas e não entram no corpus oficial.

A interface foi carregada com o índice real via Streamlit AppTest: nenhuma exceção,
42.687 avaliações, 10.994 notas 1 ou 2, 73 categorias. O servidor local retornou HTTP200
na página e no endpoint de saúde; foi encerrado após o teste. Abra `INICIAR.cmd` para iniciar.

## Execuções reais com LLM

As execuções abaixo usam o corpus completo, recuperação híbrida, top-k4 e o modelo
pequeno local. Configuração, textos, IDs, respostas e correções de citações estão
nos JSONs de `reports/examples/`. Tempos variam com equipamento e aquecimento do modelo.

| Exemplo | Resultado | Tempo (s) | Fontes |
| --- | --- | ---: | ---: |
| 01-atrasos | answered | 29.697 | 4 |
| 02-elogios | answered | 5.559 | 4 |
| 03-fora-do-escopo | abstained | 0.000 | 0 |
| 04-sem-evidencias | abstained | 0.016 | 0 |

Nos dois exemplos respondidos, os trechos produzidos foram identificados como citações
literais das fontes. Uma troca de rótulo feita pelo modelo é corrigida pela coincidência
textual e preservada em `original_evidence_ids`. Isso não demonstra correção semântica
geral: paráfrases e consultas novas ainda precisam de avaliação.

## Recuperação no pool de desenvolvimento

Pool de 17 documentos reais e cinco consultas, com quatro perguntas rotuladas por
relevância. Rótulos propostos com auxílio de IA, ainda pendentes de revisão humana.
O resultado não representa o corpus completo nem um teste independente.

| Método | Recall@4 | MRR@4 | Gate de recuperação |
| --- | ---: | ---: | ---: |
| Denso | 0,5625 | 0,875 | 5/5 |
| Híbrido | 0,675 | 1,000 | 5/5 |

O gate mede apenas menos de dois hits; não avalia o LLM. A recuperação de atraso
continuou com Recall@4 de 0,5 no pool. Ver `evaluation/README.md`, os JSONs de métricas
e `reports/development-notes.md` para erros observados e limites.

## Limites e próximos passos de entrega

- Modelo pequeno pode repetir relatos, trocar referências ou gerar sínteses inadequadas.
  A conferência literal cobre somente cópias identificáveis; revisão humana continua necessária.
- Limiar 0,75 e mínimo de duas evidências são configurações iniciais, sem calibração independente.
- Top-k não permite ranking de frequência nem percentuais populacionais dos temas.
- Falta revisão humana independente dos rótulos e da sustentação das respostas.
- Este registro foi produzido antes da publicação; o endereço de entrega está em [docs/entrega.md](../docs/entrega.md).
- Roteiro de 6 min 50 s disponível; vídeo e submissão acadêmica ainda não realizados.
