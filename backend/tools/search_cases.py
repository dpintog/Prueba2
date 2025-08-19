from typing import Optional, List, Dict, Any
from langchain.tools import tool
from providers.bot_search_client import make_search_client
import google.genai as genai
from config import settings

def _embed_query(text: str) -> List[float]:
    # Create client with API key
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    # Use the genai client for embeddings with correct API
    result = client.models.embed_content(
        model=settings.GEMINI_EMBED_MODEL,
        contents=text
    )
    return result.embeddings[0].values

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
        "search_text": query,
        "vector_queries": [{"vector": vec, "fields": "content_vector", "k": top_k, "kind": "vector"}],
        "filter": filter_str
    }

    if settings.USE_SEMANTIC_RANKER:
        kwargs.update({
            "query_type": "semantic",
            "semantic_configuration_name": settings.SEMANTIC_CONFIG_NAME,
            "query_language": "es",  # Spanish language
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
