def register_admin_handlers(bot):
    @bot.message_handler(commands=['clear_all'])
    async def clear_channel(message):

        import asyncio
        from shared.config import CHANNEL_ID
        try:
            chat_id = CHANNEL_ID
            bot_user = await bot.get_me()
            admins = await bot.get_chat_administrators(chat_id)
            bot_is_admin = any(admin.user.id == bot_user.id and admin.can_delete_messages for admin in admins)

            if not bot_is_admin:
                chat = await bot.get_chat(chat_id)
                await bot.send_message(message.chat.id, (
                    f"❌ Bot nie ma uprawnień do usuwania wiadomości na kanale {chat.title}.\n"
                    "Upewnij się, że bot jest administratorem z uprawnieniem do usuwania wiadomości."
                ))
                return

            deleted_count = 0
            message_ids = []

            for i in range(1, 101):
                try:
                    msg = await bot.get_messages(chat_id, i)
                    if msg:
                        message_ids.append(msg.message_id)
                except:
                    break

            for msg_id in message_ids:
                try:
                    await bot.delete_message(chat_id, msg_id)
                    deleted_count += 1
                    await asyncio.sleep(0.1)  
                except Exception as e:
                    print(f"Błąd usuwania wiadomości {msg_id}: {e}")

            chat = await bot.get_chat(chat_id)
            await bot.send_message(message.chat.id, f"✅ Usunięto {deleted_count} wiadomości z kanału {chat.title} (ID: {chat_id}).")
        except Exception as e:
            await bot.send_message(message.chat.id, f"❌ Błąd: {str(e)}")
            print(f"Błąd w /clear_all: {str(e)}")

    @bot.message_handler(commands=['update'])
    async def update_refresh_interval(message):

        import os, re
        from shared.config import BOT_NAME
        from handlers.sessions import load_sessions
        from services.session_service import update_intervals, DEFAULT_REFRESH_INTERVAL
        from services.session_service import refresh_other_chats
        try:
            parts = message.text.split()
            if len(parts) < 4:
                await bot.send_message(message.chat.id, "❌ Nieprawidłowy format. Użyj: /update [identyfikator] [nick] [seconds]")
                return
            identifier = parts[1].strip("[]").strip()

            if len(parts) > 3 and (parts[2].startswith('"') or parts[2].endswith('"')):
                nick_start = 2
                nick_end = len(parts)
                while nick_end > nick_start and parts[nick_end - 1].endswith('"'):
                    nick_end -= 1
                nick = " ".join(parts[nick_start:nick_end]).strip('"').strip()
            else:
                nick_parts = []
                i = 2
                while i < len(parts) and not parts[i].isdigit():
                    nick_parts.append(parts[i])
                    i += 1
                nick = " ".join(nick_parts).strip("[]").strip("@")
            try:
                interval = int(parts[-1].strip("[]").strip())
                if interval <= 0:
                    await bot.send_message(message.chat.id, "❌ Czas musi być dodatnią liczbą całkowitą!")
                    return
            except ValueError:
                await bot.send_message(message.chat.id, "❌ Czas musi być liczbą całkowitą!")
                return
            phone_number = None
            active_sessions_dict = load_sessions(BOT_NAME, force_refresh=True)
            if identifier.startswith('+'):
                phone_number = identifier
            elif identifier.isdigit():
                user_id = int(identifier)
                for pn, data in active_sessions_dict.items():
                    if data["user_id"] == user_id:
                        phone_number = pn
                        break
            else:
                username = identifier.lstrip("@")
                for pn, data in active_sessions_dict.items():
                    if data["username"] == username:
                        phone_number = pn
                        break
            if not phone_number:
                await bot.send_message(message.chat.id, f"❌ Nie znaleziono sesji dla identyfikatora {identifier}")
                return
            username = active_sessions_dict[phone_number]["username"]
            user_folder = os.path.join(os.getcwd(), BOT_NAME, "users", username)
            clean_nick = re.sub(r'[^\w\-_\. ]', '_', nick)
            original_nick = nick
            target_file_users = os.path.join(user_folder, "users", f"{clean_nick}.txt")
            target_file_groups = os.path.join(user_folder, "groups", f"{clean_nick}.txt")
            file_exists = os.path.exists(target_file_users) or os.path.exists(target_file_groups)
            if not file_exists:
                target_file_users_original = os.path.join(user_folder, "users", f"{original_nick}.txt")
                target_file_groups_original = os.path.join(user_folder, "groups", f"{original_nick}.txt")
                if not (os.path.exists(target_file_users_original) or os.path.exists(target_file_groups_original)):
                    await bot.send_message(message.chat.id, f"❌ Czat {nick} nie istnieje dla {phone_number}")
                    return
            update_intervals[(phone_number, clean_nick)] = interval
            await refresh_other_chats(phone_number, specific_nick=original_nick, interval=interval)
            await bot.send_message(message.chat.id, f"✅ Ustawiono odświeżanie dla {original_nick} na {phone_number} co {interval} sekund.")
        except Exception as e:
            await bot.send_message(message.chat.id, f"❌ Błąd: {str(e)}")
            print(f"Błąd w /update: {str(e)}")

    @bot.message_handler(commands=['invite_all'])
    async def invite_all_users(message):

        import os
        from shared.config import BOT_NAME
        data_file = os.path.join(os.getcwd(), BOT_NAME, "dane.txt")
        if not os.path.exists(data_file):
            await bot.send_message(message.chat.id, "❌ Brak zarejestrowanych użytkowników.")
            return
        with open(data_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if not lines:
            await bot.send_message(message.chat.id, "❌ Brak zarejestrowanych użytkowników.")
            return
        success_count = 0
        sent_list = "Lista użytkowników, do których wysłano zaproszenie:\n"
        for line in lines:
            try:
                parts = line.split(", ")
                user_id = int(parts[0].split("ID: ")[1].strip())
                username = parts[1].split("Nick: ")[1].strip()
                chat_id_part = parts[3].split("ChatID: ")[1].strip()
                chat_id = int(chat_id_part) if chat_id_part else None
                if username != "Brak nicku" and chat_id is not None:
                    await bot.send_message(chat_id, "Zapraszam na kanał @julciasik!")
                    sent_list += f"- {username} (ChatID: {chat_id})\n"
                    success_count += 1
            except Exception as e:
                print(f"Błąd przetwarzania linii '{line.strip()}': {str(e)}")
        await bot.send_message(message.chat.id, f"✅ Wiadomość wysłana do {success_count} użytkowników.\n{sent_list}")