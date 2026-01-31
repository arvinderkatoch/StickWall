import requests
import random
import os
import ctypes
import time
import json
import sys
from bs4 import BeautifulSoup
import keyboard

# ---------------- CONFIG ---------------- #

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "base_search_url": "https://wallhaven.cc/search",
    "user_agent": "Mozilla/5.0",
    "save_dir": os.path.join(os.getenv("TEMP"), "wallhaven"),
    "max_pages": 80
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG.copy()

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)

    return cfg


cfg = load_config()

HEADERS = {"User-Agent": cfg["user_agent"]}
SAVE_DIR = os.path.expandvars(os.path.expanduser(cfg["save_dir"]))
os.makedirs(SAVE_DIR, exist_ok=True)

# ---------------- SINGLE INSTANCE ---------------- #

def ensure_single_instance():
    mutexname = "Global\\wallhaven_wallpaper_single_instance_mutex"
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, mutexname)
    ERROR_ALREADY_EXISTS = 183
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return None
    return handle


# ---------------- WALLHAVEN LOGIC ---------------- #

def get_random_search_url():
    categories = random.choice(["100", "010", "001"])
    purity = random.choice(["100", "110"])
    sorting = random.choice(["views", "favorites", "random"])
    page = random.randint(1, cfg["max_pages"])

    return (
        f"{cfg['base_search_url']}?"
        f"categories={categories}"
        f"&purity={purity}"
        f"&sorting={sorting}"
        f"&order=desc"
        f"&page={page}"
    )


def fetch_wallpaper_page():
    url = get_random_search_url()
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    thumbs = soup.select("figure > a.preview")

    if not thumbs:
        raise Exception("No wallpapers found")

    return random.choice(thumbs)["href"]


def fetch_image_url(wall_url):
    res = requests.get(wall_url, headers=HEADERS, timeout=10)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    img = soup.find("img", id="wallpaper")

    if not img:
        raise Exception("Wallpaper image not found")

    return img["src"]


def download_image(url):
    filename = f"wall_{random.randint(100000, 999999)}.jpg"
    path = os.path.join(SAVE_DIR, filename)

    img_data = requests.get(url, headers=HEADERS, timeout=15).content
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
        print("Wallpaper changed:", image_path)
    except Exception as e:
        print("Failed:", e)


# ---------------- MAIN ---------------- #

def main():
    handle = ensure_single_instance()
    if not handle:
        print("Already running. Exiting.")
        sys.exit(0)

    try:
        change_wallpaper()
        keyboard.add_hotkey("ctrl+alt+w", change_wallpaper)

        print("Running... Press Ctrl + Alt + W to change wallpaper")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        pass
    finally:
        try:
            ctypes.windll.kernel32.ReleaseMutex(handle)
            ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            pass


if __name__ == "__main__":
    main()
