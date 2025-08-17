from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, SystemMessage
from backend.config import settings
from backend.graph.agent_graph import build_graph
from backend.prompts import SYSTEM_PROMPT
from pydantic import BaseModel, Field

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
    # Sembrar con un mensaje del sistema para hacer cumplir la política
    msgs = [SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=req.message)]
    result = graph.invoke({"messages": msgs})
    final_msg = result["messages"][-1]
    return final_msg.content  # Cadena JSON según FINAL_JSON_INSTRUCTIONS
