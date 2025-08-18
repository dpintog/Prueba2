from typing import Optional, List, Dict, Any
from langchain.tools import tool
from providers.bot_search_client import make_search_client
from providers.gemini_provider import get_gemini_client
from config import settings

def _embed_query(text: str) -> List[float]:
    genai = get_gemini_client()
    # text-embedding-004 returns {"embedding":{"values":[...]}}
    e = genai.embed_content(model=settings.GEMINI_EMBED_MODEL, content=text)
    return e["embedding"]["values"]

@tool("search_cases", return_direct=False)
def search_cases(query: str,
                 top_k: int = 6,
                 filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Busca casos en Azure AI Search (híbrido: lexical+vector) y devuelve una lista de documentos.
    Params:
      query: texto de la consulta
      top_k: número de resultados
      filters: dict OData simple, e.g., {"providencia":"CO","year":2024}
    """
    client = make_search_client()
    vec = _embed_query(query)
    filter_str = None
    if filters:
        parts = []
        for k, v in filters.items():
            if isinstance(v, str):
                parts.append(f"{k} eq '{v}'")
            elif isinstance(v, bool):
                parts.append(f"{k} eq {str(v).lower()}")
            else:
                parts.append(f"{k} eq {v}")
        filter_str = " and ".join(parts)

    kwargs = {
        "top": top_k,
        "search": query,
        "vector": {"value": vec, "fields": "content_vector", "k": top_k},
        "filter": filter_str
    }

    if settings.USE_SEMANTIC_RANKER:
        kwargs.update({
            "query_type": "semantic",
            "semantic_configuration_name": settings.SEMANTIC_CONFIG_NAME,
            "query_language": settings.SEMANTIC_LANGUAGE,
            "answers": "extractive",
            "captions": "extractive",
        })

    results = client.search(**kwargs)
    out = []
    for r in results:
        out.append({
            "id": str(r["id"]),
            "score": float(r["@search.score"]),
            "title": r.get("title"),
            "content": r.get("content"),
            "source": r.get("source"),
            "date": r.get("date"),
        })
    return out
