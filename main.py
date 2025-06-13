from telebot.async_telebot import AsyncTeleBot
import asyncio
from shared.config import BOT_TOKENS, BOT_NAME
import logging
logging.basicConfig(level=logging.DEBUG)


from handlers.verification import register_verification_handlers

bot = AsyncTeleBot(BOT_TOKENS[BOT_NAME])


@bot.message_handler(commands=['test'])
async def test_handler(message):
    print("[DEBUG] Odebrano /test")
    await bot.send_message(message.chat.id, "Bot działa!")


register_verification_handlers(bot)
    
if __name__ == "__main__":
    async def main():
        print("[INFO] Bot polling started. Waiting for messages...")
        await bot.polling()
    asyncio.run(main())