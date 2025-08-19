from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import ChannelAccount, Activity, ActivityTypes
from langchain_core.messages import HumanMessage, SystemMessage
from config import settings
from graph.agent_graph import build_graph
from prompts import SYSTEM_PROMPT
import logging
import json

logger = logging.getLogger(__name__)

class LegalBotHandler(ActivityHandler):
    def __init__(self):
        super().__init__()
        self.graph = build_graph()
        logger.info("Legal Bot Handler initialized")

    async def on_message_activity(self, turn_context: TurnContext):
        """
        Handle incoming messages from users
        """
        try:
            user_message = turn_context.activity.text
            logger.info(f"Received message: {user_message[:100]}...")

            # Validate input message
            if not user_message or not user_message.strip():
                await turn_context.send_activity(
                    MessageFactory.text("Lo siento, no he recibido ningún mensaje. ¿Podrías intentarlo de nuevo?")
                )
                return

            # Process the message using your existing graph
            msgs = [SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=user_message)]
            
            # Use default search parameters
            initial_state = {
                "messages": msgs,
                "top_k": 6,
                "filters": None
            }
            
            # Show typing indicator
            typing_activity = Activity(
                type=ActivityTypes.typing,
                from_property=ChannelAccount(id="bot", name="Legal Bot")
            )
            await turn_context.send_activity(typing_activity)
            
            result = self.graph.invoke(initial_state)
            final_msg = result["messages"][-1]
            
            if not hasattr(final_msg, 'content') or not final_msg.content:
                await turn_context.send_activity(
                    MessageFactory.text("Lo siento, no pude generar una respuesta. Por favor, inténtalo de nuevo.")
                )
                return

            # Try to parse the response as JSON for better formatting
            try:
                response_data = json.loads(final_msg.content)
                if isinstance(response_data, dict):
                    # Format the response nicely
                    formatted_response = self._format_legal_response(response_data)
                    await turn_context.send_activity(MessageFactory.text(formatted_response))
                else:
                    await turn_context.send_activity(MessageFactory.text(str(final_msg.content)))
            except json.JSONDecodeError:
                # If it's not JSON, send as plain text
                await turn_context.send_activity(MessageFactory.text(str(final_msg.content)))
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            error_message = (
                "Lo siento, ha ocurrido un error procesando tu consulta. "
                "Por favor, inténtalo de nuevo más tarde."
            )
            await turn_context.send_activity(MessageFactory.text(error_message))

    async def on_welcome_activity(self, turn_context: TurnContext):
        """
        Send a welcome message when users join the conversation
        """
        welcome_text = (
            "¡Hola! Soy tu asistente legal virtual. "
            "Puedo ayudarte con consultas sobre temas jurídicos. "
            "¿En qué puedo asistirte hoy?"
        )
        await turn_context.send_activity(MessageFactory.text(welcome_text))

    async def on_members_added_activity(self, members_added: list, turn_context: TurnContext):
        """
        Greet new members when they are added to the conversation
        """
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await self.on_welcome_activity(turn_context)

    def _format_legal_response(self, response_data: dict) -> str:
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
