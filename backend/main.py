from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage, SystemMessage
from config import settings
from graph.agent_graph import build_graph
from prompts import SYSTEM_PROMPT
from pydantic import BaseModel, Field
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity
import logging
import json
import os

# Clear any Google Cloud environment variables that might interfere
for env_var in ['GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_CLOUD_PROJECT', 'GCLOUD_PROJECT']:
    if env_var in os.environ:
        del os.environ[env_var]
        
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

# Initialize the graph for both API and Bot Framework calls
graph = build_graph()

# Initialize Bot Framework Adapter
BOT_ADAPTER_SETTINGS = BotFrameworkAdapterSettings(
    app_id=settings.MICROSOFT_APP_ID,
    app_password=settings.MICROSOFT_APP_PASSWORD
)
bot_adapter = BotFrameworkAdapter(BOT_ADAPTER_SETTINGS)

logger.info("Application initialized successfully")

class ChatRequest(BaseModel):
    message: str = Field(..., description="Pregunta del usuario en español")
    top_k: int = 6
    filters: dict | None = None

@app.get("/healthz")
def health():
    return {"status": "ok", "env": settings.ENV}

@app.get("/test-credentials")
def test_credentials():
    """Test endpoint to verify API credentials are working"""
    try:
        result = {
            "gemini_api": "NOT_TESTED",
            "azure_search": "NOT_TESTED", 
            "gemini_response": None,
            "azure_search_error": None,
            "environment_check": {},
            "debug_info": {}
        }
        
        # Check environment variables
        result["environment_check"] = {
            "GEMINI_API_KEY_exists": bool(settings.GEMINI_API_KEY),
            "GEMINI_API_KEY_length": len(settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else 0,
            "GEMINI_API_KEY_starts_with": settings.GEMINI_API_KEY[:10] + "..." if settings.GEMINI_API_KEY else "None",
            "GEMINI_CHAT_MODEL": settings.GEMINI_CHAT_MODEL,
            "AZURE_SEARCH_ENDPOINT": settings.AZURE_SEARCH_ENDPOINT,
            "AZURE_SEARCH_INDEX": settings.AZURE_SEARCH_INDEX
        }
        
        # Test Gemini API using the direct client first
        try:
            from providers.gemini_provider import get_gemini_client
            gemini_client = get_gemini_client()
            
            # Simple test call using the direct client
            test_response = gemini_client.models.generate_content(
                model=settings.GEMINI_CHAT_MODEL,
                contents="Just say 'Hello'"
            )
            
            if test_response and test_response.text:
                result["gemini_api"] = "OK (Direct Client)"
                result["gemini_response"] = test_response.text
            else:
                result["gemini_api"] = "FAILED - No response (Direct Client)"
                
        except Exception as e:
            result["gemini_api"] = f"FAILED (Direct Client): {str(e)}"
            
        # Test Gemini API using LangChain wrapper
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_CHAT_MODEL,
                temperature=0.2,
                google_api_key=settings.GEMINI_API_KEY
            )
            test_response = llm.invoke("Just say 'Hello'")
            result["debug_info"]["langchain_gemini"] = "OK"
            result["debug_info"]["langchain_response"] = str(test_response.content) if hasattr(test_response, 'content') else str(test_response)
        except Exception as e:
            result["debug_info"]["langchain_gemini"] = f"FAILED: {str(e)}"
        
        # Test Azure Search (basic client creation)
        try:
            from providers.bot_search_client import make_search_client
            search_client = make_search_client()
            result["azure_search"] = "OK"
        except Exception as e:
            result["azure_search"] = f"FAILED: {str(e)}"
            result["azure_search_error"] = str(e)
        
        return result
        
    except Exception as e:
        return {
            "error": f"Credential test failed: {str(e)}",
            "gemini_api": "FAILED", 
            "azure_search": "FAILED"
        }

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

@app.post("/api/messages")
async def messages(request: Request):
    """
    Bot Framework messaging endpoint using the official BotFrameworkAdapter.
    This is the proper way to handle Bot Framework activities.
    """
    try:
        # Get the request body and authorization header
        body = await request.json()
        activity = Activity().deserialize(body)
        auth_header = request.headers.get("Authorization", "")
        
        logger.info(f"Received Bot Framework activity: {activity.type}")
        
        # Define the bot's message handler
        async def on_message_activity(turn_context: TurnContext):
            """Handle incoming message activities"""
            try:
                user_message = turn_context.activity.text or ""
                logger.info(f"Processing message: '{user_message}'")
                
                if user_message.strip():
                    # Process the message using our existing AI logic
                    msgs = [
                        SystemMessage(content=SYSTEM_PROMPT),
                        HumanMessage(content=user_message)
                    ]
                    
                    initial_state = {
                        "messages": msgs,
                        "top_k": 6,
                        "filters": None
                    }
                    
                    result = graph.invoke(initial_state)
                    final_msg = result["messages"][-1]
                    
                    if hasattr(final_msg, 'content') and final_msg.content:
                        response_text = str(final_msg.content)
                        
                        # Clean and extract text from JSON response
                        if response_text.strip().startswith('```json'):
                            response_text = response_text.strip().replace('```json', '').replace('```', '').strip()
                        
                        if response_text.strip().startswith('{'):
                            try:
                                parsed = json.loads(response_text.strip())
                                response_text = (
                                    parsed.get('answer') or 
                                    parsed.get('response') or 
                                    parsed.get('text') or 
                                    parsed.get('message') or
                                    str(parsed)
                                )
                            except json.JSONDecodeError:
                                pass
                        
                        logger.info(f"Generated response: '{response_text[:100]}...'")
                        
                        # Send the response using turn_context.send_activity
                        await turn_context.send_activity(response_text)
                    else:
                        logger.warning("No content in AI response")
                        await turn_context.send_activity("No pude generar una respuesta. Por favor, reformula tu pregunta.")
                else:
                    logger.info("Empty message received")
                    await turn_context.send_activity("Por favor, envía un mensaje para que pueda ayudarte.")
                    
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                await turn_context.send_activity("Lo siento, ocurrió un error al procesar tu consulta. Por favor, inténtalo de nuevo.")
        
        # Define conversation update handler for welcome messages
        async def on_conversation_update_activity(turn_context: TurnContext):
            """Handle conversation update activities (like when users join)"""
            try:
                members_added = turn_context.activity.members_added or []
                bot_id = turn_context.activity.recipient.id if turn_context.activity.recipient else ""
                
                logger.info(f"ConversationUpdate: members_added={[m.id for m in members_added]}, bot_id={bot_id}")
                
                # Send welcome message if user was added
                for member in members_added:
                    if member.id != bot_id and member.id:
                        logger.info("Sending welcome message")
                        await turn_context.send_activity("¡Hola! Soy tu asistente legal consultor. Puedo ayudarte con consultas legales basadas en mi base de conocimientos. ¿En qué puedo asistirte hoy?")
                        
            except Exception as e:
                logger.error(f"Error in conversation update: {str(e)}", exc_info=True)
        
        # Main bot logic handler
        async def bot_logic(turn_context: TurnContext):
            """Main bot logic that routes to appropriate handlers"""
            if turn_context.activity.type == "message":
                await on_message_activity(turn_context)
            elif turn_context.activity.type == "conversationUpdate":
                await on_conversation_update_activity(turn_context)
            # For other activity types, we don't need to do anything
        
        # Process the activity using the BotFrameworkAdapter
        result = await bot_adapter.process_activity(activity, auth_header, bot_logic)
        
        # Return the result status
        return Response(status_code=result.status)
        
    except Exception as e:
        logger.error(f"Error in Bot Framework endpoint: {str(e)}", exc_info=True)
        # Return 200 to avoid Bot Service retries
        return Response(status_code=200)

@app.get("/")
def root():
    return {
        "message": "Legal Consultant Bot API",
        "endpoints": {
            "health": "/healthz",
            "chat": "/chat",
            "bot_messages": "/api/messages",
            "docs": "/docs"
        }
    }
