from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity
from config import settings
import logging

logger = logging.getLogger(__name__)

class BotAdapter:
    def __init__(self):
        # Create Bot Framework Adapter with settings
        adapter_settings = BotFrameworkAdapterSettings(
            app_id=settings.MICROSOFT_APP_ID,
            app_password=settings.MICROSOFT_APP_PASSWORD
        )
        
        self.adapter = BotFrameworkAdapter(adapter_settings)
        
        # Error handler
        async def on_error(context: TurnContext, error: Exception):
            logger.error(f"Bot Framework error: {error}", exc_info=True)
            await context.send_activity("Lo siento, ha ocurrido un error. Por favor, inténtalo de nuevo.")
        
        self.adapter.on_turn_error = on_error
        logger.info("Bot Framework Adapter initialized")

    def get_adapter(self):
        return self.adapter
