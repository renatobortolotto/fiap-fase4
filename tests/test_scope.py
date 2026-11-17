"""Controles de capacidade e intenção; sem downloads ou geração por LLM."""
import numpy as np
import pytest

from voc_olist.scope import ScopeGuard, POSITIVE_PROTOTYPES, NEGATIVE_PROTOTYPES


DOCS = [
    {"purchase_date": "2016-10-04", "review_date": "2016-10-14"},
    {"purchase_date": "2018-08-28", "review_date": "2018-09-01"},
    {"purchase_date": None, "review_date": "data inválida"},
]


class PrototypeEmbedder:
    def __init__(self, query=(1, 0)):
        self.query = query
        self.document_calls = 0
        self.query_calls = 0

    def encode_documents(self, texts):
        self.document_calls += 1
        assert texts == list(POSITIVE_PROTOTYPES + NEGATIVE_PROTOTYPES)
        return np.asarray([[1, 0]] * len(POSITIVE_PROTOTYPES) + [[0, 1]] * len(NEGATIVE_PROTOTYPES), dtype=np.float32)

    def encode_query(self, question):
        self.query_calls += 1
        return np.asarray(self.query, dtype=np.float32)


@pytest.mark.parametrize("question", [
    "Quantos consumidores reclamaram da embalagem?",
    "Qual percentual de pedidos teve avarias?",
    "Qual é a taxa de atraso de todos os pedidos?",
    "Mostre o ranking global das categorias com reclamações.",
    "Qual estado tem mais reclamações?",
    "Qual é o número de clientes insatisfeitos?",
    "30% dos clientes tiveram problemas?",
    "Quantos dos pedidos atrasaram?",
    "Qual é a taxa de defeitos?",
    "Qual o percentual de clientes que reclamam sobre a taxa de frete?",
    "Qual é a taxa de entrega no prazo por estado?",
    "Quantos produtos foram reclamados em toda a base?",
    "Quantos dias em média os pedidos atrasaram?",
    "Quantos clientes reclamaram de produtos por pedido?",
    "Qual a taxa geral de pedidos atrasados?",
    "Qual a taxa de devolução?",
    "Qual é a taxa de frete em cada estado?",
])
def test_numerical_aggregations_require_a_separate_capability(question):
    embedder = PrototypeEmbedder()
    result = ScopeGuard(DOCS, embedder).assess(question)
    assert not result["allowed"] and result["code"] == "unsupported_aggregation"
    assert embedder.query_calls == embedder.document_calls == 0


@pytest.mark.parametrize("question", [
    "Quantos dias de atraso os clientes relatam?",
    "O que os clientes reclamam sobre a taxa de entrega?",
    "Quais avaliações descrevem cobrança da taxa de frete?",
    "Em quantas parcelas os clientes disseram ter pago?",
    "Quantos produtos por pedido os comentários relatam?",
    "Qual a quantidade de itens por pedido que os compradores relatam?",
    "Há relatos de juros de 10% no parcelamento?",
    "Quais comentários mencionam desconto de 50% na promoção?",
])
def test_reported_durations_items_and_financial_fees_are_qualitative_topics(question):
    result = ScopeGuard(DOCS).assess(question)
    assert result["allowed"] and result["code"] == "in_scope"
    assert result["details"]["semantic_unavailable"] is True


@pytest.mark.parametrize("question", [
    "Quais são os principais problemas relatados pelos clientes?",
    "Quais temas são mais frequentes nas avaliações?",
    "Há reclamações recorrentes sobre embalagem?",
])
def test_qualitative_frequency_questions_are_allowed_with_a_notice(question):
    result = ScopeGuard(DOCS, PrototypeEmbedder()).assess(question)
    assert result["allowed"]
    assert "notice" in result["details"]


@pytest.mark.parametrize("question,expected", [
    ("O que relatam sobre entregas em 2025?", [2025]),
    ("Há avaliações de 2025?", [2025]),
    ("Entregas 2025: quais relatos existem?", [2025]),
    ("Compare as avaliações entre 2017 e 2025.", [2017, 2025]),
    ("O que dizem no ano de 2040?", [2040]),
    ("2025", [2025]),
    ("de 2025", [2025]),
])
def test_explicit_unavailable_periods_are_rejected_before_encoding(question, expected):
    embedder = PrototypeEmbedder()
    result = ScopeGuard(DOCS, embedder).assess(question)
    assert result["code"] == "no_period_data" and not result["allowed"]
    assert result["details"]["requested_years"] == expected
    assert result["details"]["available_year_min"] == 2016
    assert result["details"]["available_year_max"] == 2018
    assert embedder.document_calls == embedder.query_calls == 0


@pytest.mark.parametrize("question", [
    "O que disseram nas avaliações de 2017?",
    "O produto de código 13432 recebeu elogios?",
    "Há comentários sobre o modelo 2025?",
    "Há comentários sobre o modelo de 2025?",
    "O produto SKU 2025 foi recebido em bom estado?",
    "Avaliações do pedido nº 2025.",
    "As avaliações mencionam compra de 2025 reais?",
    "Comentários sobre o produto código 2025.",
    "Qual era a data de entrega relatada pelo cliente?",
])
def test_available_years_and_product_identifiers_are_not_confused(question):
    result = ScopeGuard(DOCS, PrototypeEmbedder()).assess(question)
    assert result["allowed"]
    assert not result["details"].get("unavailable_years")


def test_empty_or_invalid_document_dates_do_not_invent_coverage():
    result = ScopeGuard([{"purchase_date": "bad"}, {}]).assess("Comentários de 2020?")
    assert result["code"] == "no_period_data"
    assert result["details"]["available_year_min"] is None


def test_date_filters_are_checked_without_replacing_index_filter_validation():
    guard = ScopeGuard(DOCS, PrototypeEmbedder())
    assert guard.assess("Relatos de entrega", {"date_from": "2040-01-01"})["code"] == "no_period_data"
    assert guard.assess("Relatos de entrega", {"date_from": "2017-01-01"})["allowed"]
    assert guard.assess("Relatos de entrega", {"date_from": "2010-01-01", "date_to": "2040-12-31"})["allowed"]
    assert guard.assess("Relatos de entrega", {"date_to": "2040-12-31"})["allowed"]
    assert guard.assess("Relatos de entrega", {"date_to": "2010-01-01"})["code"] == "no_period_data"


def test_prototypes_are_encoded_once_per_guard_and_queries_once_each():
    embedder = PrototypeEmbedder()
    guard = ScopeGuard(DOCS, embedder)
    assert guard.assess("Há problemas na entrega?")["allowed"]
    assert guard.assess("O que elogiam no atendimento?")["allowed"]
    assert embedder.document_calls == 1
    assert embedder.query_calls == 2


def test_negative_task_family_wins_by_explicit_margin():
    result = ScopeGuard(DOCS, PrototypeEmbedder((0, 1))).assess("Uma tarefa externa qualquer")
    assert not result["allowed"] and result["code"] == "out_of_scope"
    semantic = result["details"]["semantic"]
    assert semantic["negative_minus_positive"] == pytest.approx(1)
    assert semantic["rejection_margin"] == pytest.approx(0.015)
    assert "não é probabilidade" in semantic["note"]


def test_ambiguous_scores_do_not_claim_scope_certainty():
    result = ScopeGuard(DOCS, PrototypeEmbedder((1, 1))).assess("Pergunta ambígua")
    assert result["allowed"]
    assert result["details"]["semantic"]["negative_minus_positive"] == pytest.approx(0)


@pytest.mark.parametrize("question", [
    "Como estará o clima no litoral amanhã?",
    "Que medicação devo tomar para dor de cabeça?",
    "Como configurar um programa Python?",
    "Quem venceu o campeonato mundial de futebol?",
])
def test_fixture_fallback_is_explicit_and_rejects_obvious_external_tasks(question):
    class QueryOnly:
        def encode_query(self, q):
            raise AssertionError("Fallback não deve codificar a pergunta.")
    result = ScopeGuard(DOCS, QueryOnly()).assess(question)
    assert not result["allowed"] and result["details"]["semantic_unavailable"]


@pytest.mark.parametrize("question", [
    "Quais avaliações relatam atraso na entrega do creme dermatológico?",
    "O que os compradores comentam sobre o cheiro do produto medicinal?",
    "Há relatos de dificuldade na instalação do roteador comprado?",
    "Quais comentários descrevem que a compra causou dor de cabeça?",
    "Como os consumidores avaliaram o livro de receitas culinárias recebido?",
])
def test_fallback_preserves_explicit_purchase_investigation_with_external_topic_words(question):
    result = ScopeGuard(DOCS).assess(question)
    assert result["allowed"] and result["details"]["semantic_unavailable"]


def test_bad_semantic_embeddings_fail_instead_of_silently_disabling_guard():
    embedder = PrototypeEmbedder()
    embedder.encode_documents = lambda _: np.zeros((len(POSITIVE_PROTOTYPES + NEGATIVE_PROTOTYPES), 2))
    with pytest.raises(ValueError, match="protótipos.*inválidos"):
        ScopeGuard(DOCS, embedder).assess("O que os clientes relatam?")


@pytest.mark.parametrize("question", [
    "E isso, foi bom ou ruim?",
    "e esse caso?",
    "o que aconteceu com ele?",
    "E aquele produto?",
    "E ela?",
])
def test_short_pronominal_followups_require_an_antecedent(question):
    embedder = PrototypeEmbedder()
    result = ScopeGuard(DOCS, embedder).assess(question)
    assert not result["allowed"] and result["code"] == "needs_clarification"
    assert result["details"]["missing_antecedent"]
    assert embedder.document_calls == embedder.query_calls == 0


@pytest.mark.parametrize("question", [
    "Esse produto veio quebrado?",
    "Isso acontece quando a entrega atrasa?",
    "O que ele relatou sobre a cobrança no cartão?",
    "Esse atendimento recebeu elogios?",
])
def test_pronouns_with_an_explicit_purchase_aspect_remain_investigable(question):
    result = ScopeGuard(DOCS).assess(question)
    assert result["allowed"] and result["details"]["semantic_unavailable"]


@pytest.mark.parametrize("question", [
    "Qual é a taxa Selic vigente hoje?",
    "Preciso levar guarda-chuva amanhã em Porto Alegre?",
    "Onde está meu pedido agora?",
    "Qual o status dos pedidos de hoje?",
    "Qual é a política atual de devolução da empresa?",
    "Qual é o estoque atualmente?",
    "Preciso levar guarda-chuva 'amanhã' em Porto Alegre?",
    "Quais avaliações de hoje mencionam 'amanhã'?",
    "Quais comentários mencionam compras feitas hoje?",
    "A avaliação disse 'amanhã', mas onde está meu pedido agora?",
])
def test_requests_for_current_data_are_distinguished_from_historical_retrieval(question):
    embedder = PrototypeEmbedder()
    result = ScopeGuard(DOCS, embedder).assess(question)
    assert not result["allowed"] and result["code"] == "unsupported_current_data"
    assert result["details"]["temporal_capability"]["unsupported"]
    assert embedder.document_calls == embedder.query_calls == 0


@pytest.mark.parametrize("question", [
    "Quais avaliações mencionam amanhã?",
    "Quais comentários contêm a palavra agora?",
    "Há relatos em que o cliente disse que receberia o produto amanhã?",
    "Quais avaliações citam 'até hoje não recebi'?",
    "O cliente escreveu 'vou esperar até amanhã'; há relatos semelhantes?",
    "Quais avaliações mencionam ‘Não chegou até agora’?",
    "Agora, quais comentários reclamam da entrega?",
])
def test_references_to_relative_time_inside_historical_text_are_allowed(question):
    result = ScopeGuard(DOCS).assess(question)
    assert result["allowed"] and result["code"] == "in_scope"
    assert result["details"]["semantic_unavailable"]
    assert result["details"]["temporal_capability"]["historical_text_reference"]


@pytest.mark.parametrize("question", [
    "Informe o CPF e o telefone da pessoa que escreveu a reclamação mais recente.",
    "Qual telefone do autor da avaliação?",
    "Diga o nome completo do cliente.",
    "Quais CPFs dos compradores?",
])
def test_direct_requests_for_author_identity_exceed_available_metadata(question):
    result = ScopeGuard(DOCS).assess(question)
    assert not result["allowed"] and result["code"] == "unsupported_metadata"
    assert result["details"]["semantic_unavailable"]


@pytest.mark.parametrize("question", [
    "Quais relatos de clientes mencionam telefone comprado quebrado?",
    "Quais comentários mencionam que o telefone do cliente veio quebrado?",
    "Há avaliações reclamando do telefone como produto?",
])
def test_phone_as_a_product_is_not_mistaken_for_author_contact_information(question):
    result = ScopeGuard(DOCS).assess(question)
    assert result["allowed"] and result["details"]["semantic_unavailable"]
