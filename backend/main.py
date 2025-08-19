from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, SystemMessage
from config import settings
from graph.agent_graph import build_graph
from prompts import SYSTEM_PROMPT
from pydantic import BaseModel, Field
import logging
import json
import httpx
import asyncio

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

@app.post("/api/messages")
async def bot_messages(request: Request):
    """
    Bot Framework endpoint for receiving messages
    """
    try:
        # Get the request body
        body = await request.body()
        
        # Parse the activity from the request
        if not body:
            return Response(status_code=400)
            
        try:
            activity_data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Invalid JSON in request body")
            return Response(status_code=400)
        
        # Log the complete incoming activity for debugging
        logger.info(f"Complete incoming activity: {json.dumps(activity_data, indent=2)}")
        
        # Handle different activity types
        if activity_data.get("type") == "message" and activity_data.get("text"):
            # Extract the user message
            user_message = activity_data["text"]
            logger.info(f"Bot processing message: {user_message[:100]}...")
            
            # Process the message using your existing graph
            msgs = [SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=user_message)]
            
            initial_state = {
                "messages": msgs,
                "top_k": 6,
                "filters": None
            }
            
            result = graph.invoke(initial_state)
            final_msg = result["messages"][-1]
            
            if not hasattr(final_msg, 'content') or not final_msg.content:
                response_text = "Lo siento, no pude generar una respuesta. Por favor, inténtalo de nuevo."
            else:
                # Try to parse and format the response
                try:
                    response_data = json.loads(final_msg.content)
                    if isinstance(response_data, dict):
                        response_text = format_legal_response(response_data)
                    else:
                        response_text = str(final_msg.content)
                except json.JSONDecodeError:
                    response_text = str(final_msg.content)
            
            # Send response back to the emulator
            await send_response_to_emulator(activity_data, response_text)
            
            # Return 200 to acknowledge receipt
            return Response(status_code=200)
            
        elif activity_data.get("type") == "conversationUpdate":
            # Handle conversation update (user joined)
            if activity_data.get("membersAdded"):
                for member in activity_data["membersAdded"]:
                    if member.get("id") != activity_data.get("recipient", {}).get("id"):
                        welcome_text = (
                            "¡Hola! Soy tu asistente legal virtual. "
                            "Puedo ayudarte con consultas sobre temas jurídicos. "
                            "¿En qué puedo asistirte hoy?"
                        )
                        
                        # Send welcome message back to the emulator
                        await send_response_to_emulator(activity_data, welcome_text)
                        
                        # Return 200 to acknowledge receipt
                        return Response(status_code=200)
        
        # For other activity types, return 200
        logger.info(f"Unhandled activity type: {activity_data.get('type')}")
        return Response(status_code=200)
        
    except Exception as e:
        logger.error(f"Error in bot endpoint: {str(e)}", exc_info=True)
        # Return error response instead of 500
        error_response = {
            "type": "message",
            "from": {
                "id": "bot",
                "name": "Legal Bot"
            },
            "text": "Lo siento, ha ocurrido un error procesando tu mensaje. Por favor, inténtalo de nuevo."
        }
        return error_response

async def send_response_to_emulator(original_activity: dict, response_text: str):
    """
    Send a response message back to the Bot Framework Emulator
    """
    try:
        service_url = original_activity.get("serviceUrl")
        conversation_id = original_activity.get("conversation", {}).get("id")
        
        if not service_url or not conversation_id:
            logger.error(f"Missing serviceUrl ({service_url}) or conversation ID ({conversation_id})")
            return
        
        # Create response activity
        response_activity = {
            "type": "message",
            "from": {
                "id": "bot",
                "name": "Legal Bot"
            },
            "conversation": original_activity.get("conversation"),
            "recipient": original_activity.get("from"),
            "text": response_text
        }
        
        # Send to the emulator's conversation endpoint
        url = f"{service_url}/v3/conversations/{conversation_id}/activities"
        
        logger.info(f"Sending response to: {url}")
        logger.info(f"Response text: {response_text}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=response_activity,
                headers={
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Successfully sent response to emulator: {response.status_code}")
            else:
                logger.error(f"Failed to send response to emulator: {response.status_code} - {response.text}")
                
    except Exception as e:
        logger.error(f"Error sending response to emulator: {str(e)}", exc_info=True)

def format_legal_response(response_data: dict) -> str:
    """
    Format a legal response dictionary into a user-friendly message
    """
    try:
        if "error" in response_data:
            return f"❌ Error: {response_data['error']}"
        
        formatted = ""
        
        if "answer" in response_data:
            formatted += f"📖 **Respuesta:**\n{response_data['answer']}\n\n"
        
        if "sources" in response_data and response_data["sources"]:
            formatted += "📚 **Fuentes consultadas:**\n"
            for i, source in enumerate(response_data["sources"][:3], 1):  # Limit to top 3 sources
                if isinstance(source, dict):
                    title = source.get("title", "Documento")
                    formatted += f"{i}. {title}\n"
                else:
                    formatted += f"{i}. {source}\n"
            formatted += "\n"
        
        if "confidence" in response_data:
            confidence = response_data["confidence"]
            if confidence >= 0.8:
                conf_emoji = "🟢"
            elif confidence >= 0.6:
                conf_emoji = "🟡"
            else:
                conf_emoji = "🔴"
            formatted += f"{conf_emoji} **Confianza:** {confidence:.1%}\n"
        
        return formatted.strip() if formatted else str(response_data)
        
    except Exception as e:
        logger.error(f"Error formatting response: {e}")
        return str(response_data)

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
