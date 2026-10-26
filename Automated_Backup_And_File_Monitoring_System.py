import os
import shutil
import hashlib
import logging
import smtplib
import time
import schedule
from email.message import EmailMessage

BASE_DIR = os.path.dirname(os.path.abspath(_file_))
SOURCE = os.path.join(BASE_DIR, "my_files")
BACKUP = os.path.join(BASE_DIR, "Backup")
STATE_FILE = os.path.join(BASE_DIR, "file_state.txt")

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

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
        logging.warning("Email not configured.")
        print("Email not configured.")
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = "Backup Monitoring Alert"
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER
        msg.set_content("\n".join(events))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        logging.info("Email sent successfully.")

    except Exception as error:
        logging.error(f"Email failed: {error}")
        print("Email could not be sent.")


def backup_files():
    if not os.path.isdir(SOURCE):
        print("ERROR: my_files folder not found!")
        logging.error("Source folder not found.")
        return

    os.makedirs(BACKUP, exist_ok=True)

    previous_exists = os.path.exists(STATE_FILE)

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            previous_files = set(
                line.rstrip("\n") for line in f
            )
    except FileNotFoundError:
        previous_files = set()
    except OSError as error:
        logging.error(f"Could not read state: {error}")
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

    if previous_exists:
        for relative in sorted(previous_files - current_files):
            event = f"Source file deleted: {relative}"
            events.append(event)
            logging.warning(event)

    try:
        temp_state = STATE_FILE + ".tmp"

        with open(temp_state, "w", encoding="utf-8") as f:
            for relative in sorted(current_files):
                f.write(relative + "\n")

        os.replace(temp_state, STATE_FILE)

    except OSError as error:
        logging.error(f"Could not save state: {error}")
        return

    if events:
        print("\n".join(events))
        send_email(events)
    else:
        print("Scan complete. No changes detected.")

    print("Backup scan completed.")


print("Backup Monitoring System Started!")

backup_files()
schedule.every(1).minutes.do(backup_files)

while True:
    schedule.run_pending()
    time.sleep(1)
