from typing import TypedDict, List, Any
from langchain_core.messages import BaseMessage

class GraphState(TypedDict, total=False):
    messages: List[BaseMessage]
