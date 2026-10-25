import os
import json
import shutil
import hashlib
import logging
import smtplib
import time
import schedule
from email.message import EmailMessage

# Project folders
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(BASE_DIR, "my_files")
BACKUP = os.path.join(BASE_DIR, "Backup")
STATE_FILE = os.path.join(BASE_DIR, "file_state.json")

# Email settings: set these as environment variables
EMAIL_SENDER = os.getenv("raginimohite2011@gmail.com")
EMAIL_PASSWORD = os.getenv("abcdefghijklm")
EMAIL_RECEIVER = os.getenv("hrishikharade096@gmail.com")

logging.basicConfig(
    filename=os.path.join(BASE_DIR, "backup.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def file_hash(path):
    md5 = hashlib.md5()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)

    return md5.hexdigest()


def send_email(events):
    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER]):
        logging.warning("Email not configured; alert not sent.")
        print("Email not configured. Set email environment variables.")
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = "Backup Monitoring Alert"
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER
        msg.set_content(
            "Backup monitoring report:\n\n" + "\n".join(events)
        )

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        logging.info("Email alert sent successfully.")

    except Exception as error:
        logging.error(f"Email failed: {error}")
        print("Email could not be sent. Check email settings.")


def backup_files():
    if not os.path.isdir(SOURCE):
        logging.error("Source folder not found: " + SOURCE)
        print("ERROR: my_files folder not found!")
        return

    os.makedirs(BACKUP, exist_ok=True)

    # Read previously scanned file names
    previous_exists = os.path.exists(STATE_FILE)
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            previous_files = set(json.load(f))
    except FileNotFoundError:
        previous_files = set()
    except (json.JSONDecodeError, OSError) as error:
        logging.error(f"Could not read file state: {error}")
        print("Could not read file_state.json; scan stopped.")
        return

    current_files = set()
    events = []

    for root, dirs, files in os.walk(SOURCE):
        for name in files:
            source_path = os.path.join(root, name)
            relative = os.path.relpath(source_path, SOURCE)
            current_files.add(relative)
            backup_path = os.path.join(BACKUP, relative)

            try:
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)

                if not os.path.exists(backup_path):
                    shutil.copy2(source_path, backup_path)
                    event = f"New file backed up: {relative}"
                    events.append(event)
                    logging.info(event)

                elif file_hash(source_path) != file_hash(backup_path):
                    shutil.copy2(source_path, backup_path)
                    event = f"Modified file backed up: {relative}"
                    events.append(event)
                    logging.info(event)

            except OSError as error:
                logging.error(f"File error ({relative}): {error}")

    # Detect deletions only after the first successful baseline scan
    if previous_exists:
        for relative in sorted(previous_files - current_files):
            event = f"Source file deleted: {relative}"
            events.append(event)
            logging.warning(event)

    # Save current file list for the next scan
    try:
        temp_state = STATE_FILE + ".tmp"
        with open(temp_state, "w", encoding="utf-8") as f:
            json.dump(sorted(current_files), f, indent=2)
        os.replace(temp_state, STATE_FILE)
    except OSError as error:
        logging.error(f"Could not save file state: {error}")
        print("Could not save file state; check backup.log.")
        return

    if events:
        print("\n".join(events))
        send_email(events)
    else:
        print("Scan complete. No changes detected.")

    print("Backup scan completed.")


# Run once immediately, then every minute
print("Backup Monitoring System Started!")
backup_files()
schedule.every(1).minutes.do(backup_files)

while True:
    schedule.run_pending()
    time.sleep(1)
