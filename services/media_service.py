import os
import re
import aiofiles
import time
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, User
from telethon.errors import FloodWaitError
from datetime import datetime
from shared.utils import get_client
from shared.config import BOT_NAME, TELEGRAM_OFFICIAL_ID, CHANNEL_ID
from handlers.sessions import client_locks

MEDIA_ROOT = os.path.join(os.getcwd(), os.getenv('BOT_NAME', 'bot1'), "media")

async def download_media(client, message, user_id=None, chat_id=None, notify_func=None):
    """
    Pobiera media z wiadomości i zapisuje do odpowiedniego folderu.
    notify_func: opcjonalna funkcja do powiadamiania użytkownika (np. bot.send_message)
    """
    try:
        if message.media:
            date_folder = datetime.now().strftime('%Y-%m-%d')
            user_folder = os.path.join(MEDIA_ROOT, str(user_id) if user_id else "unknown")
            date_path = os.path.join(user_folder, date_folder)
            os.makedirs(date_path, exist_ok=True)
            file_path = None
            if isinstance(message.media, MessageMediaPhoto):
                file_path = await client.download_media(message, file=date_path)
            elif isinstance(message.media, MessageMediaDocument):
                file_path = await client.download_media(message, file=date_path)
            else:
                pass
            if notify_func and file_path:
                await notify_func(chat_id, f"✅ Plik zapisany: {os.path.basename(file_path)}")
            return file_path
        else:
            if notify_func:
                await notify_func(chat_id, "⚠️ Brak mediów do pobrania w tej wiadomości.")
            return None
    except FloodWaitError as e:
        if notify_func:
            await notify_func(chat_id, f"⏳ Ograniczenie pobierania. Spróbuj ponownie za {e.seconds} sekund.")
        raise
    except Exception as e:
        if notify_func:
            await notify_func(chat_id, f"❌ Błąd pobierania pliku: {str(e)}")
        raise

def archive_media(user_id, file_path):
    """
    Przenosi pobrany plik do folderu archiwum użytkownika.
    """
    try:
        archive_folder = os.path.join(MEDIA_ROOT, str(user_id), "archive")
        os.makedirs(archive_folder, exist_ok=True)
        base_name = os.path.basename(file_path)
        archive_path = os.path.join(archive_folder, base_name)
        os.rename(file_path, archive_path)
        return archive_path
    except Exception as e:
        print(f"Błąd archiwizacji pliku: {e}")
        return None

async def refresh_media(phone_number):
    """
    Pobiera i zapisuje media z ostatnich wiadomości użytkowników (DM) dla danej sesji.
    """
    client = get_client(phone_number, f"{BOT_NAME}_session")
    async with client_locks[phone_number]:
        try:
            if not client.is_connected():
                await client.connect()
            user = await client.get_me()
            if user is None:
                print(f"Brak danych użytkownika dla {phone_number}. Resetowanie sesji...")
                session_file = client.session.filename
                if os.path.exists(session_file):
                    await client.disconnect()
                    time.sleep(1)
                    os.remove(session_file)
                await client.start(phone=phone_number)
                raise Exception("Wymagana ponowna autoryzacja sesji!")
            username = user.username if user.username else f"user_{user.id}"
            user_id = user.id
            user_base_folder = os.path.join(os.getcwd(), BOT_NAME, "users", username)
            users_folder = os.path.join(user_base_folder, "users")
            dialogs = await client.get_dialogs()
            for dialog in dialogs:
                if dialog.is_user and dialog.name and dialog.entity.id != TELEGRAM_OFFICIAL_ID:
                    base_name = re.sub(r'[^\w\-_\. ]', '_', dialog.name)
                    user_subfolder = os.path.join(users_folder, base_name)
                    has_media = False
                    async for message in client.iter_messages(dialog.entity, limit=100):
                        if message.media:
                            has_media = True
                            break
                    if has_media:
                        os.makedirs(user_subfolder, exist_ok=True)
                        file_path = os.path.join(user_subfolder, f"{base_name}.txt")
                        messages_content = f"Użytkownik: @{username}, ID: {user_id}\nRozmowa z: {dialog.name}\nNumer telefonu: {dialog.entity.phone if isinstance(dialog.entity, User) and dialog.entity.phone else 'Niedostępny'}\n\n"
                        async for message in client.iter_messages(dialog.entity, limit=100):
                            sender = await message.get_sender()
                            sender_name = sender.username if sender and sender.username else "Nieznany"
                            if message.text:
                                date_str = message.date.strftime('%Y-%m-%d %H:%M:%S')
                                messages_content += f"[{date_str}] {sender_name}: {message.text}\n"
                            if message.media:
                                media_path = os.path.join(user_subfolder, f"{message.date.strftime('%Y%m%d_%H%M%S')}")
                                if hasattr(message.media, 'photo'):
                                    media_path += ".jpg"
                                elif hasattr(message.media, 'document'):
                                    if message.media.document.attributes and hasattr(message.media.document.attributes[-1], 'file_name'):
                                        ext = message.media.document.attributes[-1].file_name.split('.')[-1]
                                    else:
                                        ext = 'mp4'
                                    media_path += f".{ext}"
                                else:
                                    continue
                                if not os.path.exists(media_path):
                                    await client.download_media(message.media, media_path)
                                    print(f"Pobrano nowy plik multimedialny: {media_path}")
                        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                            await f.write(messages_content)
        except Exception as e:
            print(f"Błąd odświeżania mediów dla {phone_number}: {e}")
        finally:
            if client.is_connected():
                await client.disconnect()