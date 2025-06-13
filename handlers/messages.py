from shared.sessions import load_pending_verifications
from shared.config import BOT_NAME
from services.user_service import get_code_keyboard

def register_message_handlers(bot):
    @bot.message_handler(func=lambda message: True, content_types=['text'])
    async def handle_text(message):
        user_id = message.from_user.id
        pending_verifications = load_pending_verifications(BOT_NAME)
        if str(user_id) in pending_verifications and pending_verifications[str(user_id)].get("awaiting_verification", False):
            await bot.send_message(
                message.chat.id,
                "❌ Użyj przycisków poniżej, aby wpisać kod weryfikacyjny.",
                reply_markup=get_code_keyboard(user_id)
            )
        else:
            await bot.send_message(message.chat.id, "👋 Rozpocznij weryfikację: /start")