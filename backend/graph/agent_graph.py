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
from prompts import SYSTEM_PROMPT, FINAL_JSON_INSTRUCTIONS
from config import settings
from .state import GraphState

tools = [search_cases, search_by_providence, get_providence_summary, list_providences]
tool_node = ToolNode(tools)

def _model():
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_CHAT_MODEL,
        temperature=0.2,
        max_output_tokens=1024,
        google_api_key=settings.GEMINI_API_KEY
    ).bind_tools(tools)

def agent(state: GraphState) -> GraphState:
    llm = _model()
    
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
        # This is the first human message, prepend system context
        original_content = valid_messages[0].content
        enhanced_content = f"{SYSTEM_PROMPT}\n\nUsuario: {original_content}"
        valid_messages[0] = HumanMessage(content=enhanced_content)
    
    try:
        resp = llm.invoke(valid_messages)
        return {"messages": state["messages"] + [resp]}
    except Exception as e:
        logger.error(f"Error invoking LLM: {str(e)}")
        logger.error(f"Valid messages count: {len(valid_messages)}")
        for i, msg in enumerate(valid_messages):
            logger.error(f"Message {i}: {type(msg).__name__} - Content length: {len(getattr(msg, 'content', '')) if hasattr(msg, 'content') else 'NO_CONTENT'}")
        # Return a fallback response
        fallback_response = AIMessage(content="Lo siento, hubo un error procesando tu consulta. Por favor, intenta de nuevo con una pregunta más específica.")
        return {"messages": state["messages"] + [fallback_response]}

def route_tools(state: GraphState):
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "call_tools"
    return "final"

def final_answer(state: GraphState) -> GraphState:
    # Ask model to synthesize final JSON-compliant answer from the conversation so far.
    llm = _model()
    
    # Create the final instruction message
    final_instruction = HumanMessage(content=FINAL_JSON_INSTRUCTIONS)
    
    # Filter valid messages and add the final instruction
    valid_messages = []
    for msg in state["messages"]:
        if isinstance(msg, ToolMessage):
            # Always include ToolMessages as they contain search results
            valid_messages.append(msg)
        elif hasattr(msg, 'content') and msg.content and str(msg.content).strip():
            valid_messages.append(msg)
        elif hasattr(msg, 'tool_calls') and msg.tool_calls:
            # Include AI messages with tool calls
            valid_messages.append(msg)
    
    if not valid_messages:
        # If no valid messages, return a default JSON response
        logger.error("No valid messages for final answer, returning default response")
        default_response = '''{"answer": "No pude procesar la consulta.", "citations": [], "cases": [], "disclaimer": "Esto no constituye asesoría legal."}'''
        return {"messages": state["messages"] + [AIMessage(content=default_response)]}
    
    msgs = valid_messages + [final_instruction]
    
    try:
        out = llm.invoke(msgs)
        return {"messages": state["messages"] + [out]}
    except Exception as e:
        logger.error(f"Error in final_answer: {str(e)}")
        logger.error(f"Final messages being sent: {[type(m).__name__ + ': ' + str(m.content)[:100] if hasattr(m, 'content') else type(m).__name__ for m in msgs]}")
        # Return a fallback JSON response
        fallback_response = '''{"answer": "Lo siento, hubo un error generando la respuesta final.", "citations": [], "cases": [], "disclaimer": "Esto no constituye asesoría legal."}'''
        return {"messages": state["messages"] + [AIMessage(content=fallback_response)]}

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
