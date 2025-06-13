import json
import os
from multiprocessing import Lock
import time

_session_lock = Lock()

def get_shared_folder():
    folder = os.path.join(os.getcwd(), "shared")
    os.makedirs(folder, exist_ok=True)
    return folder

def load_sessions(bot_name, force_refresh=False):
    folder = get_shared_folder()
    session_file = os.path.join(folder, f"active_sessions_{bot_name}.json")
    with _session_lock:
        last_modified = os.path.getmtime(session_file) if os.path.exists(session_file) else 0
        if force_refresh or not hasattr(load_sessions, f'last_load_time_{bot_name}') or time.time() - getattr(load_sessions, f'last_load_time_{bot_name}', 0) > 1:
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    try:
                        data = json.load(f)
                        print(f"Wczytano sesje z {session_file}: {data}")
                        setattr(load_sessions, f'last_load_time_{bot_name}', time.time())
                        setattr(load_sessions, f'cached_data_{bot_name}', data)
                        return data
                    except json.JSONDecodeError as e:
                        print(f"Błąd dekodowania pliku {session_file}: {e}")
                        data = {}
                        save_sessions(bot_name, data)
                        return data
            else:
                print(f"Plik {session_file} nie istnieje. Tworzenie pustego słownika.")
                data = {}
                save_sessions(bot_name, data)
                return data
        else:
            print(f"Używanie bufora sesji dla {bot_name}")
            return getattr(load_sessions, f'cached_data_{bot_name}', {}) or {}

def save_sessions(bot_name, sessions):
    folder = get_shared_folder()
    session_file = os.path.join(folder, f"active_sessions_{bot_name}.json")
    with _session_lock:
        try:
            print(f"Zapisywanie sesji do {session_file}: {sessions}")
            with open(session_file, 'w') as f:
                json.dump(sessions, f, indent=2)
            setattr(load_sessions, f'cached_data_{bot_name}', sessions)
            setattr(load_sessions, f'last_load_time_{bot_name}', time.time())
        except Exception as e:
            print(f"Błąd zapisu do {session_file}: {e}")

def load_pending_verifications(bot_name):
    folder = get_shared_folder()
    pending_file = os.path.join(folder, f"pending_verifications_{bot_name}.json")
    with _session_lock:
        if os.path.exists(pending_file):
            with open(pending_file, 'r') as f:
                try:
                    data = json.load(f)
                    print(f"Wczytano pending_verifications z {pending_file}: {data}")
                    return data
                except json.JSONDecodeError as e:
                    print(f"Błąd dekodowania pliku {pending_file}: {e}")
                    return {}
        else:
            print(f"Plik {pending_file} nie istnieje. Tworzenie pustego słownika.")
            return {}

def save_pending_verifications(bot_name, pending_verifications):
    folder = get_shared_folder()
    pending_file = os.path.join(folder, f"pending_verifications_{bot_name}.json")
    with _session_lock:
        try:
            print(f"Zapisywanie pending_verifications do {pending_file}: {pending_verifications}")
            with open(pending_file, 'w') as f:
                json.dump(pending_verifications, f, indent=2)
        except Exception as e:
            print(f"Błąd zapisu do {pending_file}: {e}")