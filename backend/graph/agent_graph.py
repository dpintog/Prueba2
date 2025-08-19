from typing import List
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from tools.search_cases import search_cases
from tools.search_by_providence import search_by_providence, get_providence_summary, list_providences
from prompts import SYSTEM_PROMPT
from config import settings
from .state import GraphState

# Create a custom tool node that can access state
class StatefulToolNode:
    def __init__(self, tools):
        self.tools = {tool.name: tool for tool in tools}
    
    def __call__(self, state: GraphState) -> GraphState:
        messages = state["messages"]
        last_message = messages[-1]
        
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return state
        
        # Get search parameters from state
        top_k = state.get("top_k", 6)
        filters = state.get("filters", None)
        
        tool_messages = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"].copy()
            
            # Inject state parameters for search tools
            if tool_name == "search_cases":
                if "top_k" not in tool_args or tool_args["top_k"] == 6:  # Use state value if default
                    tool_args["top_k"] = top_k
                if filters and ("filters" not in tool_args or not tool_args["filters"]):
                    tool_args["filters"] = filters
            elif tool_name == "search_by_providence":
                if "top_k" not in tool_args or tool_args["top_k"] == 10:  # Use state value if default
                    tool_args["top_k"] = top_k
                if filters and ("additional_filters" not in tool_args or not tool_args["additional_filters"]):
                    tool_args["additional_filters"] = filters
            
            if tool_name in self.tools:
                try:
                    result = self.tools[tool_name].invoke(tool_args)
                    tool_messages.append(
                        ToolMessage(
                            content=str(result),
                            tool_call_id=tool_call["id"]
                        )
                    )
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {str(e)}")
                    tool_messages.append(
                        ToolMessage(
                            content=f"Error ejecutando herramienta {tool_name}: {str(e)}",
                            tool_call_id=tool_call["id"]
                        )
                    )
        
        return {
            "messages": messages + tool_messages,
            "top_k": state.get("top_k"),
            "filters": state.get("filters")
        }

tools = [search_cases, search_by_providence, get_providence_summary, list_providences]
tool_node = StatefulToolNode(tools)

def _model():
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_CHAT_MODEL,
        temperature=0.2,
        max_output_tokens=1024,
        google_api_key=settings.GEMINI_API_KEY
    ).bind_tools(tools)

def agent(state: GraphState) -> GraphState:
    llm = _model()
    
    # Get search parameters from state
    top_k = state.get("top_k", 6)
    filters = state.get("filters", None)
    
    # Filter out messages with empty content to prevent Gemini API errors
    valid_messages = []
    for msg in state["messages"]:
        include_msg = False
        
        if isinstance(msg, ToolMessage):
            # Always include ToolMessages as they contain search results
            include_msg = True
        elif hasattr(msg, 'tool_calls') and msg.tool_calls:
            # This is an AI message with tool calls, keep it even if content is empty
            include_msg = True
        elif hasattr(msg, 'content') and msg.content:
            # Handle different message types - check for non-empty content
            content = str(msg.content).strip()
            if content:
                include_msg = True
        
        if include_msg:
            valid_messages.append(msg)
        else:
            logger.warning(f"Skipping message: {type(msg).__name__} - Content: '{getattr(msg, 'content', 'NO_CONTENT')}'")
    
    if not valid_messages:
        # If no valid messages, create a default response
        logger.error("No valid messages found, returning default response")
        return {"messages": state["messages"] + [AIMessage(content="Lo siento, no pude procesar tu consulta. Por favor, intenta reformular tu pregunta.")]}
    
    logger.info(f"Processing {len(valid_messages)} valid messages")
    
    # Ensure the first message includes context (for initial interactions)
    first_human_msg_idx = None
    for i, msg in enumerate(valid_messages):
        if isinstance(msg, HumanMessage):
            first_human_msg_idx = i
            break
    
    if first_human_msg_idx is not None and first_human_msg_idx == 0:
        # This is the first human message, enhance with search parameters if provided
        original_content = valid_messages[0].content
        enhanced_content = f"{SYSTEM_PROMPT}\n\nUsuario: {original_content}"
        
        # Add search parameters context if they differ from defaults
        if top_k != 6:
            enhanced_content += f"\n[Parámetro: buscar hasta {top_k} resultados]"
        if filters:
            enhanced_content += f"\n[Filtros aplicados: {filters}]"
        
        valid_messages[0] = HumanMessage(content=enhanced_content)
    
    try:
        resp = llm.invoke(valid_messages)
        return {"messages": state["messages"] + [resp], "top_k": top_k, "filters": filters}
    except Exception as e:
        logger.error(f"Error invoking LLM: {str(e)}")
        logger.error(f"Valid messages count: {len(valid_messages)}")
        for i, msg in enumerate(valid_messages):
            logger.error(f"Message {i}: {type(msg).__name__} - Content length: {len(getattr(msg, 'content', '')) if hasattr(msg, 'content') else 'NO_CONTENT'}")
        # Return a fallback response
        fallback_response = AIMessage(content="Lo siento, hubo un error procesando tu consulta. Por favor, intenta de nuevo con una pregunta más específica.")
        return {"messages": state["messages"] + [fallback_response], "top_k": top_k, "filters": filters}

def route_tools(state: GraphState):
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "call_tools"
    return "final"

def final_answer(state: GraphState) -> GraphState:
    # Get the last AI message directly instead of asking for JSON synthesis
    messages = state["messages"]
    
    # Find the last AI message that contains actual content
    last_ai_message = None
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and hasattr(msg, 'content') and msg.content and str(msg.content).strip():
            # Skip messages with tool calls, we want the actual response
            if not (hasattr(msg, 'tool_calls') and msg.tool_calls):
                last_ai_message = msg
                break
    
    if last_ai_message:
        # Use the existing AI response
        return {"messages": state["messages"]}
    else:
        # If no suitable AI message found, create a simple fallback
        logger.error("No suitable AI message found for final answer")
        fallback_response = AIMessage(content="Lo siento, no pude procesar tu consulta adecuadamente. Por favor, intenta reformular tu pregunta.")
        return {"messages": state["messages"] + [fallback_response]}

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
