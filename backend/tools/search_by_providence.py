from typing import List, Dict, Any, Optional
from langchain.tools import tool
from providers.bot_search_client import make_search_client


@tool("search_by_providence", return_direct=False)
def search_by_providence(providence: str, 
                        top_k: int = 10,
                        additional_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Busca todos los documentos correspondientes a una providencia específica en Azure AI Search.
    Retorna todos los campos excepto el embedding (content_vector).
    
    Params:
      providence: el identificador de la providencia a buscar (ej: "T-123/2024")
      top_k: número máximo de resultados a retornar (default: 10)
      additional_filters: filtros adicionales opcionales como año, fuente, etc.
    
    Returns:
      Lista de documentos con todos los campos disponibles excepto content_vector
    """
    client = make_search_client()
    
    # Build the filter for providence
    filters = [f"title eq '{providence}'"]
    
    # Add additional filters if provided
    if additional_filters:
        for key, value in additional_filters.items():
            if isinstance(value, str):
                filters.append(f"{key} eq '{value}'")
            elif isinstance(value, bool):
                filters.append(f"{key} eq {str(value).lower()}")
            else:
                filters.append(f"{key} eq {value}")
    
    filter_str = " and ".join(filters)
    
    # Execute search with filter
    try:
        results = client.search(
            search_text="*",  # Search all documents
            filter=filter_str,
            top=top_k,
            select=[
                "id", "title", "content", "source", "date", "year", 
                "relevance", "tema_subtema_raw", "temas"
            ]  # Exclude content_vector
        )
        
        documents = []
        for result in results:
            doc = {
                "id": result.get("id"),
                "title": result.get("title"),
                "content": result.get("content"),
                "source": result.get("source"),
                "date": result.get("date"),
                "year": result.get("year"),
                "relevance": result.get("relevance"),
                "tema_subtema_raw": result.get("tema_subtema_raw"),
                "temas": result.get("temas", []),
                "search_score": float(result.get("@search.score", 0.0))
            }
            documents.append(doc)
        
        return documents
        
    except Exception as e:
        # Return error information for debugging
        return [{
            "error": f"Error searching for providence '{providence}': {str(e)}",
            "providence": providence,
            "filters_used": filter_str
        }]


@tool("get_providence_summary", return_direct=False)
def get_providence_summary(providence: str) -> Dict[str, Any]:
    """
    Obtiene un resumen de información sobre una providencia específica,
    incluyendo estadísticas y metadatos agregados.
    
    Params:
      providence: el identificador de la providencia a resumir
    
    Returns:
      Diccionario con resumen de la providencia
    """
    documents = search_by_providence(providence, top_k=100)
    
    if not documents or (len(documents) == 1 and "error" in documents[0]):
        return {
            "providence": providence,
            "found": False,
            "error": documents[0].get("error") if documents else "No documents found"
        }
    
    # Calculate summary statistics
    total_chunks = len(documents)
    sources = set(doc.get("source") for doc in documents if doc.get("source"))
    dates = [doc.get("date") for doc in documents if doc.get("date")]
    years = [doc.get("year") for doc in documents if doc.get("year")]
    relevances = [doc.get("relevance") for doc in documents if doc.get("relevance")]
    all_temas = []
    for doc in documents:
        if doc.get("temas"):
            all_temas.extend(doc.get("temas"))
    
    unique_temas = list(set(all_temas))
    
    # Get the most relevant content (highest relevance score)
    most_relevant = max(documents, key=lambda x: x.get("relevance", 0)) if relevances else None
    
    summary = {
        "providence": providence,
        "found": True,
        "total_chunks": total_chunks,
        "sources": list(sources),
        "dates": list(set(dates)) if dates else [],
        "years": list(set(years)) if years else [],
        "average_relevance": sum(relevances) / len(relevances) if relevances else 0,
        "max_relevance": max(relevances) if relevances else 0,
        "min_relevance": min(relevances) if relevances else 0,
        "unique_temas": unique_temas,
        "tema_count": len(unique_temas),
        "most_relevant_content": {
            "content": most_relevant.get("content", "")[:500] + "..." if most_relevant and most_relevant.get("content") else "",
            "relevance": most_relevant.get("relevance") if most_relevant else 0,
            "tema_subtema": most_relevant.get("tema_subtema_raw") if most_relevant else ""
        } if most_relevant else None
    }
    
    return summary


@tool("list_providences", return_direct=False)
def list_providences(limit: int = 50, 
                    source_filter: Optional[str] = None,
                    year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Lista las providencias únicas disponibles en el índice con información básica.
    
    Params:
      limit: número máximo de providencias únicas a retornar
      source_filter: filtrar por fuente específica (opcional)
      year_filter: filtrar por año específico (opcional)
    
    Returns:
      Lista de providencias únicas con información básica
    """
    client = make_search_client()
    
    # Build filters
    filters = []
    if source_filter:
        filters.append(f"source eq '{source_filter}'")
    if year_filter:
        filters.append(f"year eq {year_filter}")
    
    filter_str = " and ".join(filters) if filters else None
    
    try:
        # Use facets to get unique providences (titles)
        search_params = {
            "search_text": "*",
            "facets": ["title"],
            "top": 0  # We only want facets, not documents
        }
        
        if filter_str:
            search_params["filter"] = filter_str
            
        results = client.search(**search_params)
        
        providences = []
        facets = results.get_facets()
        
        if "title" in facets:
            for facet in facets["title"][:limit]:
                providence_name = facet["value"]
                count = facet["count"]
                
                # Get a sample document for this providence to get additional info
                sample_doc = client.search(
                    search_text="*",
                    filter=f"title eq '{providence_name}'" + (f" and {filter_str}" if filter_str else ""),
                    top=1,
                    select=["source", "date", "year", "relevance", "tema_subtema_raw"]
                )
                
                sample = next(iter(sample_doc), {})
                
                providences.append({
                    "providence": providence_name,
                    "document_count": count,
                    "source": sample.get("source"),
                    "date": sample.get("date"),
                    "year": sample.get("year"),
                    "relevance": sample.get("relevance"),
                    "tema_subtema": sample.get("tema_subtema_raw")
                })
        
        return providences
        
    except Exception as e:
        return [{
            "error": f"Error listing providences: {str(e)}",
            "filters_used": filter_str
        }]
