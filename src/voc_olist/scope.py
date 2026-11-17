"""Controles de intenção e capacidade antes da recuperação de avaliações.

O cosseno com uma avaliação não prova que a tarefa pode ser respondida pela base.
Este guard separa investigação qualitativa de agregações indisponíveis, períodos
sem registros e tarefas externas. A comparação com protótipos E5 é uma heurística
de desenvolvimento: a margem não é uma probabilidade nem uma garantia de escopo.
"""
from __future__ import annotations

from datetime import date
import re
import unicodedata

import numpy as np


# Protótipos descrevem famílias de tarefas, sem IDs, fontes ou respostas do corpus.
# As duas famílias usam o mesmo encoder/prefixos da recuperação. Não são rótulos
# humanos de avaliação. Uma alteração requer reavaliar paráfrases e casos ambíguos.
POSITIVE_PROTOTYPES = (
    "Investigar o que clientes relatam sobre suas experiências de compra em lojas de comércio eletrônico.",
    "Consultar comentários e avaliações de consumidores sobre problemas, reclamações e elogios aos produtos comprados.",
    "Analisar relatos de clientes sobre entrega dos pedidos, demora, prazo e recebimento antecipado.",
    "Encontrar experiências dos compradores com embalagem, transporte, peças faltantes e produtos danificados.",
    "Investigar opiniões sobre qualidade, tamanho, cor e diferenças entre o produto recebido e o anúncio da loja.",
    "Ler relatos sobre atendimento da loja, solicitações de troca, cancelamento, devolução e reembolso de compras.",
    "Analisar avaliações que descrevem pagamento da compra, frete, parcelamento e problemas na cobrança do cartão.",
    "Consultar opiniões de compradores sobre cheiro, qualidade e entrega de cosméticos, cremes e produtos de cuidado pessoal.",
    "Investigar como consumidores avaliam o manual, a instalação e o funcionamento de equipamentos que compraram.",
    "Encontrar elogios e experiências positivas nas avaliações dos produtos e do serviço da loja.",
)

NEGATIVE_PROTOTYPES = (
    "Consultar previsão meteorológica, temperatura, chuva e condições do tempo para uma cidade e data.",
    "Descobrir informações de geografia, história, capitais de países e fatos de conhecimento geral.",
    "Aprender a instalar programas, configurar software, escrever código e resolver erros de programação.",
    "Pedir um script ou código de programação para processar arquivos e automatizar tarefas computacionais.",
    "Receber recomendação médica, indicação de medicamento, diagnóstico ou tratamento de sintomas e doenças.",
    "Escolher um remédio para aliviar dor, tratar sintomas ou decidir qual tratamento de saúde usar.",
    "Saber resultados de partidas, campeões, placares e fatos históricos de campeonatos esportivos.",
    "Receber orientação de investimentos, cotação de moedas, ações e aplicações financeiras.",
    "Pedir uma receita culinária e instruções de preparo de alimentos.",
    "Solicitar criação de poema, texto criativo, tradução ou resolução de exercícios escolares.",
    "Consultar notícias atuais, legislação, política e informações oficiais externas às experiências de compra.",
)

# Margem inicial de desenvolvimento, deliberadamente conservadora: só rejeita
# semanticamente quando uma tarefa externa supera TODAS as famílias de compra.
# Não foi calibrada como estimador de risco; o gerador ainda precisa se abster
# quando as fontes não sustentam a resposta, inclusive nos casos admitidos aqui.
SEMANTIC_MARGIN = 0.015

QUALITATIVE_NOTICE = (
    "Posso descrever os temas presentes nos comentários recuperados. Essa amostra "
    "por relevância não permite medir quais são os mais frequentes em toda a base."
)

_YEAR = re.compile(r"(?<!\d)(?:19|20|21)\d{2}(?!\d)")
_DATE_WORDS = re.compile(r"\b(?:ano|anos|periodo|compras?|entregas?|pedidos?|avaliacoes?|comentarios?)\b")
_IDENTIFIER_PREFIX = re.compile(
    r"\b(?:sku|codigo|cod\.?|modelo|model|id|identificador|numero|produto)"
    r"\s*[:#-]?\s*(?:de\s+)?$|\bpedido\s+(?:n[ºo.]?|numero)\s*[:#-]?\s*$"
)


def _fold(text: str) -> str:
    return " ".join(
        "".join(character for character in unicodedata.normalize("NFKD", text.casefold())
                if not unicodedata.combining(character)).split()
    )


def _needs_antecedent(question: str) -> bool:
    """Um seguimento pronominal curto não traz o contexto da conversa.

    Só considera frases compostas por referência, avaliação e palavras genéricas.
    Um aspecto explícito, como 'quebrado', 'entrega' ou 'cobrança', já torna a
    pergunta investigável; não se proíbe toda ocorrência de 'isso' ou 'esse'.
    """
    words = re.findall(r"[a-z0-9]+", _fold(question))
    pronouns = {
        "isso", "isto", "aquilo", "ele", "ela", "eles", "elas", "esse", "essa", "esses", "essas",
        "este", "esta", "estes", "estas", "aquele", "aquela", "aqueles", "aquelas", "dele", "dela",
        "deles", "delas", "disso", "disto", "daquilo",
    }
    generic = {
        "a", "o", "as", "os", "um", "uma", "uns", "umas", "e", "que", "quem", "qual", "quais",
        "quando", "como", "foi", "foram", "era", "eram", "ser", "esta", "estava", "ficou", "vai",
        "bom", "boa", "bons", "boas", "ruim", "ruins", "melhor", "pior", "certo", "errado",
        "aconteceu", "acontece", "acontecer", "caso", "casos", "coisa", "coisas", "situacao",
        "problema", "problemas", "resultado", "final", "produto", "produtos", "pedido", "pedidos",
        "compra", "compras", "sobre", "com", "para", "pra", "por", "de", "do", "da", "dos", "das",
        "ao", "aos", "ou", "ai", "aqui", "ali", "entao", "afinal", "mesmo", "pode", "poderia",
        "me", "conte", "diga", "explique", "deu", "veio", "chegou", "valeu", "pena", "no", "na",
    }
    return bool(words and len(words) <= 12 and set(words) & pronouns
                and all(word in pronouns or word in generic for word in words))


_QUOTED = re.compile(r'"[^"\n]*"|“[^”\n]*”|\'[^\'\n]*\'|‘[^’\n]*’')
_CURRENT_TIME = re.compile(r"\b(?:hoje|agora|amanha|atualmente|vigente|atual|atuais|em tempo real|neste momento)\b")
_REVIEW_REFERENCE = re.compile(
    r"\b(?:avaliacao|avaliacoes|comentarios?|relatos?|textos?|mensagens?|reclamacao|reclamacoes|"
    r"clientes?|consumidores?|compradores?)\b"
)


def _temporal_capability(question: str) -> dict:
    """Distingue informação atual de referência a um trecho histórico.

    'Avaliações de hoje' pede registros atuais; 'avaliações que mencionam hoje'
    procura linguagem dentro de textos históricos. Aspas preservam o segundo uso,
    mas não neutralizam outro pedido atual fora delas. Nenhuma data relativa é
    convertida silenciosamente para a data de uma avaliação antiga.
    """
    original = _fold(question)
    all_terms = sorted({match.group() for match in _CURRENT_TIME.finditer(original)})
    if not all_terms:
        return {"unsupported": False, "terms": [], "historical_text_reference": False}
    unquoted = _fold(_QUOTED.sub(" ", question))
    review_reference = bool(_REVIEW_REFERENCE.search(unquoted))
    if not review_reference:
        # Aspas decorativas em uma pergunta externa não a transformam em busca
        # textual: 'vou precisar de guarda-chuva "amanhã"?' ainda pede previsão.
        unquoted = original
    # 'Agora, quais comentários...' pode ser apenas uma transição de assunto.
    # O mesmo tratamento não vale para 'onde está meu pedido agora'.
    if review_reference:
        unquoted = re.sub(r"^(?:e\s+)?agora\s*[,;:\-]\s*", "", unquoted)
    unprotected = []
    for match in _CURRENT_TIME.finditer(unquoted):
        prefix = unquoted[:match.start()]
        direct_text_mention = bool(review_reference and re.search(
            r"\b(?:mencionam|menciona|mencionou|citam|cita|citou|contem|incluem|inclui|usam|usa|falam|fala)\s+"
            r"(?:(?:a|o|as|os|palavra|palavras|termo|termos|expressao|expressoes|frase|frases|ate|de)\s+)*$", prefix))
        reported_clause = bool(review_reference and re.search(
            r"\b(?:disse|disseram|escreveu|escreveram|relatou|relataram|relata|relatam|comentou|"
            r"comentaram|comentam|afirmou|afirmaram|diz|dizem)\s+que\b[^.!?;]*$", prefix))
        if not direct_text_mention and not reported_clause:
            unprotected.append(match.group())
    return {
        "unsupported": bool(unprotected),
        "terms": all_terms,
        "unprotected_terms": sorted(set(unprotected)),
        "historical_text_reference": review_reference and not unprotected,
    }


def _requests_author_identity(question: str) -> bool:
    """Falta capacidade de vincular identificadores públicos à pessoa autora.

    Telefones também são produtos: exige um pedido direto de campo pessoal e uma
    relação explícita com autor/cliente. Procurar relatos de aparelho quebrado não
    é um pedido de identidade, mesmo se mencionar o telefone de um cliente.
    """
    text = re.sub(r"[\"'“”‘’]", " ", _fold(question))
    field = r"(?:cpfs?|telefones?|celular|contato|endereco|nome completo|identidade)"
    direct_request = re.search(
        rf"\b(?:informe|mostre|revele|forneca|diga|identifique|descubra|encontre|obtenha)\s+(?:(?:o|a|os|as|me)\s+)*{field}\b|"
        rf"\b(?:qual|quais)\s+(?:(?:e|sao|o|a|os|as)\s+)*{field}\b", text)
    author_relation = re.search(
        rf"\b{field}\s+(?:pessoal\s+)?(?:do|da|dos|das|de)\s+(?:(?:o|a|os|as)\s+)?"
        r"(?:autor|autora|autores|autoras|clientes?|consumidores?|compradores?|pessoas?|quem escreveu)\b", text)
    return bool(direct_request and author_relation)


def _explicit_years(question: str) -> list[int]:
    """Reconhece contexto temporal; não interpreta todo código de 4 dígitos como ano.

    'em 2025', 'ano de 2025', 'entregas de 2025' e intervalos são temporais.
    'modelo 2025', 'SKU 2025', 'pedido nº 2025' e um código de 5 dígitos não são.
    Não se presume que o ano de fabricação/modelo seja o período da compra.
    """
    text = _fold(question)
    years = set()
    for match in _YEAR.finditer(text):
        before = text[:match.start()]
        prefix = before[-70:]
        if _IDENTIFIER_PREFIX.search(prefix):
            continue
        if re.match(r"\s*(?:reais|brl|cm|mm|gb|mb|kg|mah|ml|watts?|unidades|pecas)\b", text[match.end():]):
            continue
        explicit = bool(re.search(r"\b(?:em|de|durante|desde|ate|entre|ano(?:s)?(?:\s+de)?|no\s+ano\s+de)\s*$", prefix))
        if re.search(r"\bde\s*$", prefix) and _DATE_WORDS.search(prefix):
            explicit = True
        if re.search(r"\b(?:compras|entregas|pedidos|avaliacoes|comentarios)\s*$", prefix):
            explicit = True
        if re.search(r"(?:19|20|21)\d{2}\s*(?:a|e|ate|-)\s*$", prefix) and _DATE_WORDS.search(text):
            explicit = True
        if not before.strip() and (not text[match.end():].strip(" ?.:;") or _DATE_WORDS.search(text[match.end():])):
            explicit = True
        if explicit:
            years.add(int(match.group()))
    return sorted(years)


def _aggregation_request(question: str) -> bool:
    text = _fold(question)
    # A unidade e a operação importam: contar clientes/reviews/pedidos exige um
    # agregador; encontrar relatos de quantos DIAS demorou, quantas PARCELAS foram
    # cobradas ou quantos ITENS vieram em um pedido não exige contagem do corpus.
    # 'Taxa' também pode significar uma cobrança de frete, não um KPI populacional.
    entities = (
        r"(?:clientes|consumidores|compradores|pessoas|usuarios|avaliacoes|comentarios|reviews|"
        r"pedidos|compras|reclamacoes|ocorrencias|casos|devolucoes|cancelamentos)"
    )
    quantified_entities = rf"\bquant(?:os|as)\s+(?:(?:dos|das|de|desses|dessas|destes|destas|outros|outras|diferentes)\s+)*{entities}\b"
    if re.search(quantified_entities, text):
        return True
    if re.search(rf"\b(?:numero|quantidade|total|contagem)\s+(?:total\s+)?de\s+{entities}\b", text):
        return True
    global_context = bool(re.search(
        r"\b(?:toda a base|base inteira|todo o corpus|corpus inteiro|populacao|global|em todos os pedidos)\b", text))
    quantitative_operation = bool(re.search(
        r"\b(?:quantos|quantas|numero|quantidade|total|contagem|percentual|porcentagem|percentagem|proporcao)\b|%", text))
    if global_context and quantitative_operation:
        return True
    if re.search(r"\bem media\b|\b(?:calcule|calcular|qual|quais)\b.*\b(?:media|mediana|desvio padrao)\b", text):
        return True
    kpi_rate = re.search(
        r"\btaxas?\s+(?:(?:geral|media|global|total)\s+)?(?:(?:de|dos|das)\s+)?"
        r"(?:atrasos?|defeitos?|avarias?|cancelamentos?|devolu(?:cao|coes)|retornos?|"
        r"reclama(?:cao|coes)|insatisfacao|satisfacao|entregas?\s+(?:no prazo|atrasadas?|com atraso)|"
        r"pedidos\s+(?:atrasados|no prazo|com atraso)|produtos\s+(?:com defeitos?|defeituosos))\b", text)
    if kpi_rate or (re.search(r"\btaxas?\b", text) and re.search(r"\b(?:por|em cada)\s+(?:estado|estados|categoria|categorias)\b", text)):
        return True
    # Um percentual de clientes/pedidos é populacional mesmo se o tema for juros.
    # Já 'relatos de juros de10%' pode ser respondido citando a cobrança narrada.
    if re.search(rf"(?:%|\bpercentual|\bpercentuais|\bporcentagem|\bpercentagem|\bproporcao)\s+(?:de|dos|das|do|da)\s+{entities}\b", text):
        return True
    reported_financial_topic = (
        re.search(r"\b(?:relat(?:os?|am|aram|ad[oa]s?)|comentarios|avaliacoes|reclamam|descrevem|disseram|dizem|mencionam|citam|informam)\b", text)
        and re.search(r"\b(?:juros|frete|parcelamento|descontos?|encargos?|tarifas?|cobrancas?)\b|\btaxa\s+de\s+entrega\b", text)
    )
    if re.search(r"%|\b(?:percentual|percentuais|porcentagem|percentagem|proporcao)\b", text) and not reported_financial_topic:
        return True
    if re.search(r"\b(?:ranking|rankear|classificacao)\b", text) and re.search(r"\b(?:global|geral|base|estados|estado|categorias|categoria|todos|todas)\b", text):
        return True
    if re.search(r"\b(?:qual|quais)\s+(?:o\s+|a\s+)?(?:estado|estados|categoria|categorias)\b", text) and re.search(r"\b(?:mais|maior|menor|melhor|pior|lidera)\b", text):
        return True
    return False


def _fallback_external_task(question: str) -> bool:
    """Fallback limitado para testes sem encoder; não simula uma decisão semântica.

    Uma pergunta explicitamente sobre relatos/opiniões de compradores pode citar
    instalação, saúde ou alimentos como assunto do produto. O tipo de investigação
    deve prevalecer sobre a simples presença dessas palavras.
    """
    text = _fold(question)
    review_task = bool(re.search(r"\b(?:avaliacoes|comentarios|relatos|reclamacoes|elogios|compradores|consumidores)\b", text))
    if review_task:
        return False
    patterns = (
        r"\b(?:clima|previsao meteorologica|previsao do tempo)\b|\bvai\s+(?:chover|fazer sol)\b",
        r"\b(?:medicacao|diagnostico)\b|\b(?:remedio|medicamento|tratamento)\b.*\b(?:dor|doenca|sintoma)\b",
        r"\b(?:instalar|configurar|programar|compilar)\b.*\b(?:software|python|javascript|programa|linux|windows)\b",
        r"\bquem\s+(?:ganhou|venceu|descobriu|inventou)\b|\bcapital\s+(?:do|da|de)\b",
        r"\b(?:cotacao|investimentos|acoes da bolsa|cambio)\b",
        r"\b(?:receita culinaria|como preparar|como cozinhar|escreva um poema)\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


class ScopeGuard:
    """Avalia intenção/capacidade; não certifica a veracidade de uma resposta."""

    def __init__(self, documents: list, embedder=None):
        self.embedder = embedder
        self._prototypes = None
        self._years = set()
        self._purchase_min = self._purchase_max = None
        for document in documents:
            for key in ("purchase_date", "review_date"):
                value = document.get(key)
                if isinstance(value, str):
                    try:
                        parsed = date.fromisoformat(value[:10])
                        self._years.add(parsed.year)
                        if key == "purchase_date":
                            self._purchase_min = min(self._purchase_min, parsed) if self._purchase_min else parsed
                            self._purchase_max = max(self._purchase_max, parsed) if self._purchase_max else parsed
                    except ValueError:
                        pass

    @staticmethod
    def _result(allowed: bool, code: str, reason: str, details: dict) -> dict:
        return {"allowed": allowed, "code": code, "reason": reason, "details": details}

    def _semantic(self, question: str) -> dict | None:
        if not callable(getattr(self.embedder, "encode_documents", None)) or not callable(getattr(self.embedder, "encode_query", None)):
            return None
        if self._prototypes is None:
            texts = list(POSITIVE_PROTOTYPES + NEGATIVE_PROTOTYPES)
            vectors = np.asarray(self.embedder.encode_documents(texts), dtype=np.float32)
            if vectors.ndim != 2 or vectors.shape[0] != len(texts) or vectors.shape[1] < 1:
                raise ValueError("Embeddings dos protótipos de escopo têm dimensão inválida.")
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            if not np.isfinite(vectors).all() or not np.isfinite(norms).all() or (norms <= 0).any():
                raise ValueError("Embeddings dos protótipos de escopo são inválidos.")
            self._prototypes = vectors / norms
        query = np.asarray(self.embedder.encode_query(question), dtype=np.float32)
        norm = np.linalg.norm(query)
        if query.ndim != 1 or query.shape[0] != self._prototypes.shape[1] or not np.isfinite(query).all() or not np.isfinite(norm) or norm <= 0:
            raise ValueError("Embedding da pergunta é inválido para o controle de escopo.")
        scores = np.clip(self._prototypes @ (query / norm), -1, 1)
        split = len(POSITIVE_PROTOTYPES)
        positive = int(np.argmax(scores[:split]))
        negative = int(np.argmax(scores[split:]))
        return {
            "method": "e5_task_prototypes",
            "positive_score": float(scores[positive]),
            "negative_score": float(scores[split + negative]),
            "negative_minus_positive": float(scores[split + negative] - scores[positive]),
            "rejection_margin": SEMANTIC_MARGIN,
            "positive_prototype": POSITIVE_PROTOTYPES[positive],
            "negative_prototype": NEGATIVE_PROTOTYPES[negative],
            "note": "Margem heurística de desenvolvimento; não é probabilidade nem garantia de escopo.",
        }

    def assess(self, question: str, filters: dict | None = None) -> dict:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Informe uma pergunta não vazia para verificar o escopo.")
        available = (callable(getattr(self.embedder, "encode_documents", None))
                     and callable(getattr(self.embedder, "encode_query", None)))
        details: dict = {"semantic_unavailable": not available}
        if _needs_antecedent(question):
            details["missing_antecedent"] = True
            return self._result(False, "needs_clarification",
                "Não consigo identificar a que você se refere. Informe o produto ou o aspecto da compra que deseja analisar.", details)
        if _requests_author_identity(question):
            return self._result(False, "unsupported_metadata",
                "A base usada não vincula CPF, nome completo ou telefone pessoal aos autores das avaliações. Posso analisar os relatos, sem atribuir identidade ou contato a uma pessoa.", details)
        temporal = _temporal_capability(question)
        if temporal["terms"]:
            details["temporal_capability"] = temporal
        if temporal["unsupported"]:
            return self._result(False, "unsupported_current_data",
                "Esta base é histórica e não consulta informações atuais, previsões ou o status de pedidos em tempo real. Posso analisar as experiências descritas nas avaliações disponíveis.", details)
        if _aggregation_request(question):
            return self._result(False, "unsupported_aggregation",
                "Esta busca não calcula contagens, percentuais ou rankings sobre toda a base. Posso apresentar relatos e temas das avaliações recuperadas.", details)
        years = _explicit_years(question)
        if years:
            minimum = min(self._years) if self._years else None
            maximum = max(self._years) if self._years else None
            unavailable = [year for year in years if minimum is None or not minimum <= year <= maximum]
            details.update(requested_years=years, available_year_min=minimum, available_year_max=maximum,
                           unavailable_years=unavailable)
            if unavailable:
                period = f"de {minimum} a {maximum}" if minimum is not None else "sem datas válidas"
                return self._result(False, "no_period_data",
                    f"A base carregada tem registros {period} e não sustenta o período solicitado. Escolha um período disponível para investigar os relatos.", details)
        # Filtros representam intervalos, não uma exigência de cobertura em cada
        # extremo. Por isso [2010,2040] pode conter dados de2016-18, enquanto
        # date_from=2040 não contém. Não confundir uma janela ampla com ausência.
        bounds = {}
        for key in ("date_from", "date_to"):
            value = (filters or {}).get(key)
            if isinstance(value, str):
                try:
                    bounds[key] = date.fromisoformat(value)
                except ValueError:
                    pass  # O índice continuará responsável por filtros inválidos.
        inverted = ("date_from" in bounds and "date_to" in bounds
                    and bounds["date_from"] > bounds["date_to"])
        if bounds and not inverted:
            outside = self._purchase_min is None
            outside = outside or bounds.get("date_from", date.min) > (self._purchase_max or date.max)
            outside = outside or bounds.get("date_to", date.max) < (self._purchase_min or date.min)
            details["filter_period"] = {
                **{key: value.isoformat() for key, value in bounds.items()},
                "available_purchase_start": self._purchase_min.isoformat() if self._purchase_min else None,
                "available_purchase_end": self._purchase_max.isoformat() if self._purchase_max else None,
            }
            if outside:
                return self._result(False, "no_period_data",
                    "O período filtrado não contém datas de compra disponíveis na base carregada. Escolha um período disponível para investigar os relatos.", details)
        if temporal["historical_text_reference"]:
            # O conteúdo de uma citação pode parecer uma tarefa externa ao E5,
            # mas buscar esse conteúdo nos relatos continua sendo exploração da
            # base. A suficiência das fontes ainda será verificada pelo RAG.
            details["method"] = "explicit_historical_text_reference"
            return self._result(True, "in_scope", "", details)
        semantic = self._semantic(question)
        if semantic is None:
            details["semantic_unavailable"] = True
            details["method"] = "limited_deterministic_fallback"
            external = _fallback_external_task(question)
        else:
            details["semantic"] = semantic
            external = semantic["negative_minus_positive"] >= SEMANTIC_MARGIN
        if external:
            return self._result(False, "out_of_scope",
                "Consigo investigar relatos e opiniões de clientes sobre compras na Olist. Essa pergunta pede informações ou orientações externas a essas avaliações.", details)
        if re.search(r"\b(?:mais frequentes?|mais comum|mais comuns|principa(?:l|is)|recorrentes?)\b", _fold(question)):
            details["notice"] = QUALITATIVE_NOTICE
        return self._result(True, "in_scope", "", details)
