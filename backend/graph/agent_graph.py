from typing import List
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from backend.tools.search_tool import search_cases
from backend.tools.list_recent_tool import list_recent_cases
from backend.prompts import SYSTEM_PROMPT, FINAL_JSON_INSTRUCTIONS
from backend.config import settings
from .state import GraphState

tools = [search_cases, list_recent_cases]
tool_node = ToolNode(tools)

def _model():
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_CHAT_MODEL,
        temperature=0.2,
        max_output_tokens=1024
    ).bind_tools(tools)

def agent(state: GraphState) -> GraphState:
    llm = _model()
    resp = llm.invoke(state["messages"])
    return {"messages": state["messages"] + [resp]}

def route_tools(state: GraphState):
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "call_tools"
    return "final"

def final_answer(state: GraphState) -> GraphState:
    # Ask model to synthesize final JSON-compliant answer from the conversation so far.
    llm = _model()
    msgs = state["messages"] + [HumanMessage(content=FINAL_JSON_INSTRUCTIONS)]
    out = llm.invoke(msgs)
    return {"messages": state["messages"] + [out]}

def build_graph():
    g = StateGraph(GraphState)
    g.add_node("agent", agent)
    g.add_node("tools", tool_node)
    g.add_node("final", final_answer)

    g.set_entry_point("agent")
    g.add_conditional_edges("agent", route_tools,
                            {"call_tools": "tools", "final": "final"})
    g.add_edge("tools", "agent")
    g.add_edge("final", END)
    return g.compile()
