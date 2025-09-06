# 🕵️ System Logger

**System Logger** is a background tool that logs everything: keystrokes, screenshots, copied text, and system info.  
It sends everything straight to a Telegram chat automatically.

⚠️ **For educational purposes only. Don’t do dumb illegal shit.**

---

## What It Does
- Logs every key you press  
- Sends any text you copy  
- Takes a screenshot every 5 minutes  
- Collects system info (hostname, IP, OS, processor, etc.)  
- Adds itself to Windows startup  
- Sends everything to Telegram  

---

## How to Use
1. Download or clone the project  
2. Open the script and add your Telegram bot token and chat ID  
3. Install the required Python libraries:
   ```bash
   pip install opencv-python pyautogui pyperclip pynput requests

4. Run the script — it starts logging right away and sends data to your Telegram




---

Main Files

logger.py — main script

.bat file — created automatically to run on Windows startup



---

Warning

This is for testing and learning only — use it on your own PC.
Running it on someone else’s machine without permission is illegal. If you do that, you're on your own.