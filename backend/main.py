from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, SystemMessage
from config import settings
from graph.agent_graph import build_graph
from prompts import SYSTEM_PROMPT
from pydantic import BaseModel, Field
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME)

if settings.CORS_ALLOW_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

graph = build_graph()

class ChatRequest(BaseModel):
    message: str = Field(..., description="Pregunta del usuario en español")
    top_k: int = 6
    filters: dict | None = None

@app.get("/healthz")
def health():
    return {"status": "ok", "env": settings.ENV}

@app.post("/chat")
def chat(req: ChatRequest):
    try:
        logger.info(f"Received chat request: {req.message[:100]}...")
        
        # Validate input message
        if not req.message or not req.message.strip():
            logger.warning("Empty message received")
            return {"error": "El mensaje no puede estar vacío"}
        
        # Sembrar con un mensaje del sistema para hacer cumplir la política
        msgs = [SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=req.message)]
        
        logger.info("Invoking graph with messages")
        # Pass search parameters to the graph state
        initial_state = {
            "messages": msgs,
            "top_k": req.top_k,
            "filters": req.filters
        }
        result = graph.invoke(initial_state)
        final_msg = result["messages"][-1]
        
        # Ensure we have content to return
        if not hasattr(final_msg, 'content') or not final_msg.content:
            logger.error("No content in final message")
            return {"error": "No se pudo generar una respuesta"}
        
        logger.info("Successfully generated response")
        return final_msg.content  # Cadena JSON según FINAL_JSON_INSTRUCTIONS
        
    except Exception as e:
        # Log the error for debugging
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        return {
            "error": "Error interno del servidor",
            "message": "No se pudo procesar la consulta. Por favor, inténtalo de nuevo.",
            "details": str(e) if settings.ENV == "dev" else None
        }
