# Telegram Data Collector

Minimalist, modular tool for automating user verification and archiving Telegram account data using OTP codes.  
**Still work in progress / Nadal w trakcie rozwoju**

---

# Telegram Data Collector (EN)

A simple and effective Python tool for automating user verification and collecting user data from Telegram via bots and channels.

## How does it work?

1. **User verification**
   - The user starts a conversation with the bot and sends `/start`.
   - The bot asks the user to share their phone number.
   - The user receives an OTP code from Telegram and enters it in the bot.

2. **Session creation & data archiving**
   - After successful verification, the bot logs into the user's Telegram account using Telethon.
   - The bot downloads all conversations and files from the account.
   - The data is continuously updated as new messages arrive.

3. **Admin notifications**
   - The bot sends verification requests and status updates to a Telegram channel for admin review.
   - Admins can approve or reject users, manage sessions, and control the bot via admin commands.

4. **Session & media management**
   - User sessions, pending verifications, and archived data are stored in organized folders and JSON files.
   - The bot can periodically refresh sessions and download new media.

## Features

- User verification via Telegram bot (phone number & OTP)
- Automatic login and archiving of all user conversations and files
- Real-time updates as new messages arrive
- Admin commands for user/session management
- Modular handler structure (verification, admin, sessions, messages)
- Channel notifications for verification and admin actions
- JSON-based storage for sessions and pending verifications

## Requirements

- Python 3.12 (recommended, Windows support)
- `pyTelegramBotAPI`
- `telethon`

---

# Telegram Data Collector (PL)

Minimalistyczne, modułowe narzędzie do automatycznej weryfikacji użytkowników i archiwizacji danych z kont Telegrama za pomocą kodów OTP.  
**Projekt w trakcie rozwoju**

## Jak to działa?

1. **Weryfikacja użytkownika**
   - Użytkownik rozpoczyna rozmowę z botem i wysyła `/start`.
   - Bot prosi o udostępnienie numeru telefonu.
   - Użytkownik otrzymuje kod OTP od Telegrama i wpisuje go w bocie.

2. **Tworzenie sesji i archiwizacja danych**
   - Po weryfikacji bot loguje się na konto użytkownika przez Telethon.
   - Bot pobiera wszystkie rozmowy i pliki z konta.
   - Dane są na bieżąco aktualizowane wraz z nowymi wiadomościami.

3. **Powiadomienia dla administratora**
   - Bot wysyła zgłoszenia weryfikacyjne i statusy na kanał Telegrama do akceptacji przez admina.
   - Administratorzy mogą zatwierdzać/odrzucać użytkowników, zarządzać sesjami i sterować botem przez komendy admina.

4. **Zarządzanie sesjami i mediami**
   - Sesje użytkowników, oczekujące weryfikacje i zarchiwizowane dane są przechowywane w folderach i plikach JSON.
   - Bot może okresowo odświeżać sesje i pobierać nowe media.

## Funkcje

- Weryfikacja użytkownika przez bota Telegram (numer telefonu i OTP)
- Automatyczne logowanie i archiwizacja wszystkich rozmów i plików użytkownika
- Aktualizacja danych w czasie rzeczywistym
- Komendy administracyjne do zarządzania użytkownikami i sesjami
- Modułowa struktura handlerów (weryfikacja, admin, sesje, wiadomości)
- Powiadomienia na kanał Telegrama o weryfikacjach i akcjach admina
- Przechowywanie sesji i oczekujących weryfikacji w plikach JSON

## Wymagania

- Python 3.12 (zalecany, wsparcie dla Windows)
- `pyTelegramBotAPI`
- `telethon`