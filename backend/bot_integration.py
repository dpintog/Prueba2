"""
Azure Bot Service integration for the Legal Consultant Bot.
This module handles the Bot Framework messaging protocol.
"""

import sys
import traceback
from datetime import datetime
from typing import Any

from botbuilder.core import (
    ActivityHandler,
    MessageFactory,
    TurnContext,
)
from botbuilder.schema import Activity, ActivityTypes
from langchain_core.messages import HumanMessage, SystemMessage

from config import settings
from graph.agent_graph import build_graph
from prompts import SYSTEM_PROMPT
import logging

logger = logging.getLogger(__name__)

class LegalConsultantBot(ActivityHandler):
    """
    Bot that integrates with the existing LangGraph-based legal consultant.
    """
    
    def __init__(self):
        super().__init__()
        self.graph = build_graph()
        logger.info("LegalConsultantBot initialized")

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        """
        Handle incoming messages from users via Bot Framework.
        """
        try:
            user_message = turn_context.activity.text
            logger.info(f"Received message from Bot Framework: {user_message[:100]}...")
            
            if not user_message or not user_message.strip():
                await turn_context.send_activity(
                    MessageFactory.text("Por favor, envía un mensaje para que pueda ayudarte.")
                )
                return
            
            # Process the message using the existing LangGraph setup
            response = await self._process_legal_query(user_message)
            
            # Send response back through Bot Framework
            await turn_context.send_activity(MessageFactory.text(response))
            
        except Exception as e:
            logger.error(f"Error processing Bot Framework message: {str(e)}", exc_info=True)
            await turn_context.send_activity(
                MessageFactory.text(
                    "Lo siento, ocurrió un error al procesar tu consulta. "
                    "Por favor, inténtalo de nuevo."
                )
            )

    async def _process_legal_query(self, user_message: str) -> str:
        """
        Process the user query using the existing LangGraph logic.
        """
        try:
            # Create messages for the graph
            msgs = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_message)
            ]
            
            # Invoke the graph with default parameters
            initial_state = {
                "messages": msgs,
                "top_k": 6,
                "filters": None
            }
            
            result = self.graph.invoke(initial_state)
            final_msg = result["messages"][-1]
            
            if not hasattr(final_msg, 'content') or not final_msg.content:
                return "No pude generar una respuesta. Por favor, reformula tu pregunta."
            
            # Return the content directly as text for Bot Framework
            content = final_msg.content
            
            # If content is JSON, try to extract a readable response
            if isinstance(content, str) and content.startswith('{'):
                try:
                    import json
                    parsed = json.loads(content)
                    # Look for common response fields
                    if 'response' in parsed:
                        return parsed['response']
                    elif 'answer' in parsed:
                        return parsed['answer']
                    elif 'message' in parsed:
                        return parsed['message']
                    else:
                        # Return the JSON formatted nicely
                        return json.dumps(parsed, indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    pass
            
            return str(content)
            
        except Exception as e:
            logger.error(f"Error in legal query processing: {str(e)}", exc_info=True)
            return "Ocurrió un error al procesar tu consulta legal. Por favor, inténtalo de nuevo."

    async def on_welcome_activity(self, turn_context: TurnContext) -> None:
        """
        Send a welcome message when users join the conversation.
        """
        welcome_text = (
            "¡Hola! Soy tu asistente legal consultor. "
            "Puedo ayudarte con consultas legales basadas en mi base de conocimientos. "
            "¿En qué puedo asistirte hoy?"
        )
        
        for member in turn_context.activity.members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(MessageFactory.text(welcome_text))

    async def on_members_added_activity(
        self, members_added: list, turn_context: TurnContext
    ) -> None:
        """
        Handle when new members are added to the conversation.
        """
        await self.on_welcome_activity(turn_context)
