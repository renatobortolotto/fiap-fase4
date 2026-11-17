"""Interface local: python -m streamlit run app.py"""
from dataclasses import replace
import json
from pathlib import Path

import streamlit as st

from voc_olist.config import Settings, generation_defaults
from voc_olist.cli import make_embedder, make_search_index
from voc_olist.llm import make_generator
from voc_olist.rag import RagService
from voc_olist.retrieval import VectorIndex

st.set_page_config(page_title="Escuta | Voz do Cliente", page_icon="◉", layout="wide")


@st.cache_resource
def load_index(path, fingerprint, retrieval_mode):
    settings = Settings.from_env()
    return make_search_index(VectorIndex.load(Path(path)), replace(settings, retrieval_mode=retrieval_mode))


@st.cache_resource
def resources(settings, fingerprint):
    index = load_index(str(settings.index_dir), fingerprint, settings.retrieval_mode)
    return RagService(index, make_embedder(settings), make_generator(settings), settings)


def render_result(result):
    if result["status"] == "answered":
        st.markdown("Nos comentários recuperados, os clientes relatam:")
        for finding in result["findings"]:
            st.markdown(finding["text"])
        st.caption("Contexto consultado: " + ", ".join(result["context_evidence_ids"]))
        with st.expander("Trechos ilustrativos", expanded=True):
            for quote in result["illustrative_quotes"]:
                st.caption(quote["evidence_id"])
                st.text(quote["quote"])
            st.caption("Exemplos do contexto; não são uma prova individual de cada frase da síntese.")
    elif result["status"] == "evidence_only":
        st.info(result["reason"])
    else:
        st.warning(result["reason"])
    st.caption(result["notice"])
    if result.get("inferred_period"):
        st.caption("Período identificado na pergunta; filtros efetivos: " + json.dumps(result["filters"], ensure_ascii=False))
    with st.expander(f"Avaliações recuperadas · {len(result['sources'])}", expanded=True):
        for source in result["sources"]:
            st.markdown(f"**{source['citation_id']} · nota {source.get('score', '?')}/5**")
            st.text(source["context_text"])
            st.caption(f"Documento: {source['doc_id']}\n"
                       f"Review: {source.get('review_id')} | Pedido: {source.get('order_id')}\n"
                       f"Compra: {source.get('purchase_date') or 'não informada'} | "
                       f"Categorias: {', '.join(source.get('categories', [])) or 'não informadas'} | "
                       f"Similaridade: {source['similarity']:.3f}")
            st.divider()
    st.download_button("Baixar resposta e evidências", json.dumps(result, ensure_ascii=False, indent=2),
                       file_name="consulta-olist.json", mime="application/json", key="export-" + result["timestamp_utc"])


st.caption("TECH CHALLENGE · FASE 4")
st.title("Escuta — Voz do Cliente")
st.write("Explore o que os clientes relatam sobre suas compras, com sínteses, contexto consultado e trechos rastreáveis.")

settings = Settings.from_env()
manifest_path = settings.index_dir / "manifest.json"
if not manifest_path.exists():
    st.info("Prepare a base e crie o índice para começar.")
    st.code("python -m voc_olist download\npython -m voc_olist prepare\npython -m voc_olist index", language="shell")
    st.stop()

try:
    index = load_index(str(settings.index_dir), manifest_path.stat().st_mtime_ns, settings.retrieval_mode)
except (ValueError, OSError) as exc:
    st.error(str(exc))
    st.stop()

with st.sidebar:
    st.header("Exploração")
    modes = {"RAG local · Qwen 7B": "native", "RAG com Ollama": "ollama",
             "RAG com Transformers": "transformers", "Somente evidências": "evidence"}
    label = st.selectbox("Modo de resposta", list(modes), index=list(modes.values()).index(settings.provider))
    provider = modes[label]
    if provider != settings.provider:
        model, revision = generation_defaults(provider)
        settings = replace(settings, provider=provider, llm_model=model, llm_revision=revision)
    if provider == "native":
        st.caption("Qwen 7B quantizado, executado neste computador. O primeiro uso baixa cerca de 4,7 GB e pode demorar; o runtime local inicia automaticamente.")
    elif provider == "transformers":
        st.caption(f"Modelo: {settings.llm_model}. O padrão baixa cerca de 3 GB no primeiro uso; a geração em CPU pode demorar.")
    elif provider == "ollama":
        st.caption(f"Modelo: {settings.llm_model}. O Ollama precisa estar em execução.")
    else:
        st.caption("Este modo recupera comentários. Para demonstrar o RAG completo, use um modo com geração.")
    scores = st.slider("Notas das avaliações", 1, 5, (1, 5))
    categories = sorted({c for d in index.documents for c in d.get("categories", [])})
    category = st.selectbox("Categoria do produto", ["Todas"] + categories)
    late = st.selectbox("Situação da entrega", ["Todas", "Com atraso", "Sem atraso"])
    dates = [d["purchase_date"] for d in index.documents if d.get("purchase_date")]
    date_filter = st.checkbox("Filtrar por período da compra", disabled=not dates) and bool(dates)
    if not dates:
        st.caption("Período indisponível: a base não contém datas de compra.")
    if date_filter:
        from datetime import date
        date_from = st.date_input("De", date.fromisoformat(min(dates)), key="date_from")
        date_to = st.date_input("Até", date.fromisoformat(max(dates)), key="date_to")
    st.caption("Datas ou categorias desconhecidas são excluídas quando o respectivo filtro está ativo.")
    if st.button("Limpar histórico"):
        st.session_state.pop("history", None)
        st.rerun()

col1, col2, col3 = st.columns(3)
col1.metric("Avaliações com texto", f"{len(index.documents):,}".replace(",", "."))
col2.metric("Notas 1 e 2", f"{sum(d['score'] <= 2 for d in index.documents):,}".replace(",", "."))
col3.metric("Categorias disponíveis", len(categories))
st.caption("Contagens calculadas sobre todo o corpus textual, antes dos filtros e da busca.")

filters = {"score_min": scores[0], "score_max": scores[1]}
if category != "Todas":
    filters["category"] = category
if late != "Todas":
    filters["delivered_late"] = late == "Com atraso"
if date_filter:
    filters.update(date_from=date_from.isoformat(), date_to=date_to.isoformat())

with st.expander("Exemplos de investigação"):
    st.write("• O que os clientes relatam sobre atrasos na entrega?\n"
             "• Quais problemas aparecem nos comentários de clientes insatisfeitos?\n"
             "• Quais experiências positivas são descritas nas avaliações?\n"
             "• Qual será o faturamento da empresa em 2027? (fora do escopo)")

for item in st.session_state.get("history", []):
    with st.chat_message("user"):
        st.write(item["question"])
    with st.chat_message("assistant"):
        render_result(item)

question = st.chat_input("Pergunte sobre as experiências de compra", max_chars=2000)
if question:
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Buscando avaliações e preparando a resposta…"):
                service = resources(settings, manifest_path.stat().st_mtime_ns)
                result = service.answer(question, filters)
            render_result(result)
            st.session_state.setdefault("history", []).append(result)
        except (ValueError, RuntimeError, OSError) as exc:
            st.error(str(exc))
