from services.session_service import generate_active_sessions_list
from shared.config import BOT_NAME

def register_session_handlers(bot):
    @bot.message_handler(commands=['sessions'])
    async def show_sessions(message):
        session_list = await generate_active_sessions_list()
        await bot.send_message(message.chat.id, f"Lista sesji:\n{session_list}")