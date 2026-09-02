from dataclasses import dataclass
import re
import unicodedata

@dataclass
class Fragment:
    document: str
    pagina: int
    texto: str
    score: int

@dataclass
class RetrievalContext:
    fragments: list[Fragment]

STOPWORDS = {
    "de","la","el","los","las","un","una","unos","unas","y","o","en","a","por",
    "para","con","del","al","que","se","su","sus","es","son","como","no","lo",
    "una","por","más","muy","ha","han","haber","ser","fue","este","esta","estos","estas",
}


def _tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return [t for t in re.findall(r"[a-z0-9]{3,}", text) if t not in STOPWORDS]


def _chunks(page_text: str, size: int, overlap: int):
    if len(page_text) <= size:
        return [page_text]
    out = []
    start = 0
    while start < len(page_text):
        end = min(len(page_text), start + size)
        out.append(page_text[start:end])
        if end == len(page_text):
            break
        start = max(0, end - overlap)
    return out


def build_relevant_context(query: str, documents, settings) -> RetrievalContext:
    query_tokens = set(_tokens(query))
    all_candidates = []

    for document in documents:
        document_candidates = []
        for page in document.pages:
            for chunk in _chunks(page["texto"], settings.chunk_size, settings.chunk_overlap):
                tokens = set(_tokens(chunk))
                overlap = len(query_tokens.intersection(tokens))
                phrase_bonus = 5 if any(
                    term in chunk.lower()
                    for term in [
                        "manual de convivencia", "siee", "falta", "deber",
                        "prohibido", "tipo i", "tipo ii", "tipo iii",
                        "artículo", "capítulo", "numeral"
                    ]
                ) else 0
                score = overlap * 10 + phrase_bonus
                if score > 0:
                    document_candidates.append(
                        Fragment(document.name, page["pagina"], chunk, score)
                    )

        document_candidates.sort(key=lambda x: x.score, reverse=True)
        all_candidates.extend(document_candidates)

    # Garantiza representación de cada documento seleccionado cuando exista
    # evidencia relevante, evitando que el ranking global excluya por completo
    # al SIEE o al Manual.
    per_document = max(1, settings.top_k // max(1, len(documents)))
    selected = []
    used_keys = set()

    for document in documents:
        candidates = [f for f in all_candidates if f.document == document.name]
        for fragment in candidates[:per_document]:
            key = (fragment.document, fragment.pagina, fragment.texto)
            if key not in used_keys:
                selected.append(fragment)
                used_keys.add(key)

    remaining = [f for f in all_candidates if (f.document, f.pagina, f.texto) not in used_keys]
    remaining.sort(key=lambda x: x.score, reverse=True)
    selected.extend(remaining[: max(0, settings.top_k - len(selected))])

    selected.sort(key=lambda x: x.score, reverse=True)
    return RetrievalContext(fragments=selected[: settings.top_k])
