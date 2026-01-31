import requests
import random
import os
import ctypes
import time
import json
import sys
from bs4 import BeautifulSoup
import keyboard   # NEW

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "search_url": "https://wallhaven.cc/search?sorting=views&order=desc",
    "user_agent": "Mozilla/5.0",
    "save_dir": os.path.join(os.getenv("TEMP"), "wallhaven")
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # Ensure defaults for missing keys
    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)
    return cfg

cfg = load_config()

def validate_config(cfg):
    # Validate search_url is a non-empty http(s) URL; fall back to default otherwise
    url = cfg.get("search_url")
    if not isinstance(url, str) or not url.strip().lower().startswith(("http://", "https://")):
        print("Warning: invalid or missing 'search_url' in config.json. Falling back to default.")
        cfg["search_url"] = DEFAULT_CONFIG["search_url"]

    # Ensure user_agent is present and sane
    ua = cfg.get("user_agent")
    if not isinstance(ua, str) or not ua.strip():
        cfg["user_agent"] = DEFAULT_CONFIG["user_agent"]

    return cfg

cfg = validate_config(cfg)
SEARCH_URL = cfg["search_url"]
HEADERS = {"User-Agent": cfg.get("user_agent", DEFAULT_CONFIG["user_agent"]) }
raw_save_dir = cfg.get("save_dir", DEFAULT_CONFIG["save_dir"])
SAVE_DIR = os.path.expandvars(os.path.expanduser(raw_save_dir))
os.makedirs(SAVE_DIR, exist_ok=True)


def ensure_single_instance():
    """Returns a mutex handle if first instance, otherwise None."""
    mutexname = "Global\\wallhaven_wallpaper_single_instance_mutex"
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, mutexname)
    last_error = ctypes.windll.kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    if last_error == ERROR_ALREADY_EXISTS:
        return None
    return handle

def fetch_wallpaper_page():
    res = requests.get(SEARCH_URL, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    thumbs = soup.select("figure > a.preview")
    return random.choice(thumbs)["href"]

def fetch_image_url(wall_url):
    res = requests.get(wall_url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    img = soup.find("img", id="wallpaper")
    return img["src"]

def download_image(url):
    path = os.path.join(SAVE_DIR, "wallpaper.jpg")
    img_data = requests.get(url, headers=HEADERS).content
    with open(path, "wb") as f:
        f.write(img_data)
    return path

def set_wallpaper(path):
    ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)

def change_wallpaper():
    try:
        wall_page = fetch_wallpaper_page()
        image_url = fetch_image_url(wall_page)
        image_path = download_image(image_url)
        set_wallpaper(image_path)
        print("Wallpaper changed")
    except Exception as e:
        print("Failed:", e)

def main():
    # Enforce single instance
    handle = ensure_single_instance()
    if not handle:
        print("Another instance is already running. Exiting.")
        sys.exit(0)

    try:
        # Change once on start
        change_wallpaper()

        # Register shortcut
        keyboard.add_hotkey("ctrl+alt+w", change_wallpaper)

        # Keep app alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        # Release mutex and close handle
        try:
            ctypes.windll.kernel32.ReleaseMutex(handle)
            ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            pass


if __name__ == "__main__":
    main()
