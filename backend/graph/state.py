from typing import TypedDict, List, Any, Dict, Optional
from langchain_core.messages import BaseMessage

class GraphState(TypedDict, total=False):
    messages: List[BaseMessage]
    top_k: Optional[int]
    filters: Optional[Dict[str, Any]]
