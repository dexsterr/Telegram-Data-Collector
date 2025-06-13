from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os

def save_user_data(user_id, username, phone_number, chat_id):
    data_file = os.path.join(os.getcwd(), "bot1", "dane.txt")
    try:
        current_data = []
        if os.path.exists(data_file):
            with open(data_file, "r", encoding="utf-8") as f:
                current_data = f.readlines()
        updated = False
        new_data = []
        for line in current_data:
            if f"ID: {user_id}" in line:
                new_data.append(f"ID: {user_id}, Nick: {username}, Numer: {phone_number}, ChatID: {chat_id}\n")
                updated = True
            else:
                new_data.append(line)
        if not updated:
            new_data.append(f"ID: {user_id}, Nick: {username}, Numer: {phone_number}, ChatID: {chat_id}\n")
        with open(data_file, "w", encoding="utf-8") as f:
            f.writelines(new_data)
    except Exception as e:
        print(f"Błąd zapisu danych użytkownika: {e}")

def get_code_keyboard(user_id):
    markup = InlineKeyboardMarkup(row_width=5)
    digits = [InlineKeyboardButton(str(i), callback_data=f"digit_{i}_{user_id}") for i in range(10)]
    markup.add(*digits)
    markup.add(InlineKeyboardButton("Wyczyść", callback_data=f"clear_{user_id}"))
    markup.add(InlineKeyboardButton("Zatwierdź", callback_data=f"submit_{user_id}"))
    return markup

def get_verification_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Zatwierdź", callback_data=f"verify_yes_{user_id}"),
        InlineKeyboardButton("❌ Odrzuć", callback_data=f"verify_no_{user_id}")
    )
    markup.add(InlineKeyboardButton("📝 Format", callback_data=f"verify_format_{user_id}"))
    return markup