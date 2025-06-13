import asyncio
from shared.sessions import load_sessions, save_sessions
from shared.config import BOT_NAME, API_ID, API_HASH, PHONE_NUMBERS, ADMIN_CHAT_ID
from telethon import TelegramClient
from datetime import datetime
import os

client_locks = {}

def get_client(phone_number, session_name=None):
    session_path = os.path.join(os.getcwd(), BOT_NAME, "sessions", f"{session_name or BOT_NAME}_session_{phone_number.replace('+', '')}")
    if phone_number not in client_locks:
        client_locks[phone_number] = asyncio.Lock()
    return TelegramClient(session_path, API_ID, API_HASH)

async def generate_active_sessions_list():
    active_sessions_dict = load_sessions(BOT_NAME, force_refresh=True)
    if not active_sessions_dict:
        return "ℹ️ Brak aktywnych sesji."
    from datetime import datetime
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    session_list = f"Lista sesji (stan na {current_date}):\n"
    for phone_number, session_data in active_sessions_dict.items():
        session_list += f"- Numer: {phone_number}, Nick: @{session_data.get('username', 'Brak')}, Status: ONLINE\n"
    return session_list

async def start_periodic_refresh(bot, interval=300):
    """
    Okresowo odświeża sesje Telethona, sprawdza statusy i powiadamia admina o zmianach.
    """
    while True:
        try:
            active_sessions = load_sessions(BOT_NAME, force_refresh=True)
            for phone_number in PHONE_NUMBERS:
                client = get_client(phone_number)
                async with client_locks[phone_number]:
                    try:
                        await client.connect()
                        if await client.is_user_authorized():
                            user = await client.get_me()
                            active_sessions[phone_number] = {
                                "phone_number": phone_number,
                                "user_id": user.id,
                                "username": user.username if user.username else f"user_{user.id}"
                            }
                        else:
                            if phone_number in active_sessions:
                                del active_sessions[phone_number]
                    except Exception as e:
                        if phone_number in active_sessions:
                            del active_sessions[phone_number]
                        await bot.send_message(ADMIN_CHAT_ID, f"❌ Sesja {phone_number} rozłączona: {str(e)}")
                    finally:
                        if client.is_connected():
                            await client.disconnect()
            save_sessions(BOT_NAME, active_sessions)
        except Exception as e:
            await bot.send_message(ADMIN_CHAT_ID, f"❌ Błąd odświeżania sesji: {str(e)}")
        await asyncio.sleep(interval)