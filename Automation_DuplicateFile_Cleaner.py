import sys
import os
import hashlib
import schedule
import time
import smtplib
import logging
from datetime import datetime
from email.message import EmailMessage

# Email Configuration
SENDER_EMAIL = "raginimohite2011@gmail.com"
SENDER_PASSWORD = "wkqhuixeuzajjmyz"
RECEIVER_EMAIL = "hrishikharade096@gmail.com"

# Logging Configuration
logging.basicConfig(
    filename="duplicate_cleaner.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def CalculateChecksum(FileName):
    fobj = open(FileName, "rb")

    hobj = hashlib.md5()

    Buffer = fobj.read(1024)

    while len(Buffer) > 0:
        hobj.update(Buffer)
        Buffer = fobj.read(1024)

    fobj.close()

    return hobj.hexdigest()


def FindDuplicate(DirectoryName):
    Ret = False

    Ret = os.path.exists(DirectoryName)

    if Ret == False:
        print("Path is invalid")
        logging.error("Path is invalid: %s", DirectoryName)
        return

    Ret = os.path.isdir(DirectoryName)

    if Ret == False:
        print("It is not a directory")
        logging.error("Not a directory: %s", DirectoryName)
        return

    Duplicate = {}

    for FolderName, SubFolder, FileName in os.walk(DirectoryName):
        for fname in FileName:
            fname = os.path.join(FolderName, fname)

            try:
                Checksum = CalculateChecksum(fname)

                if Checksum in Duplicate:
                    Duplicate[Checksum].append(fname)
                else:
                    Duplicate[Checksum] = [fname]

            except OSError as e:
                print("Unable to read file:", fname)
                logging.error("Unable to read %s: %s", fname, e)

    logging.info("Duplicate scan completed for %s", DirectoryName)

    return Duplicate


def DeleteDuplicate(DirectoryName):
    MyDict = FindDuplicate(DirectoryName)

    if MyDict is None:
        return

    Result = list(filter(lambda x: len(x) > 1, MyDict.values()))

    TotalDeleted = 0
    Report = []

    Report.append("Duplicate File Cleaner Report")
    Report.append("Timestamp: " + str(datetime.now()))
    Report.append("Directory: " + DirectoryName)
    Report.append("")

    for value in Result:
        # Keep the first file and delete only the remaining duplicates
        for subvalue in value[1:]:
            try:
                os.remove(subvalue)
                TotalDeleted += 1

                print("Deleted:", subvalue)
                logging.info("Deleted duplicate file: %s", subvalue)

                Report.append("Deleted: " + subvalue)

            except OSError as e:
                print("Unable to delete:", subvalue)
                logging.error("Unable to delete %s: %s", subvalue, e)

                Report.append("Failed to delete: " + subvalue)

    print("Total deleted files:", TotalDeleted)

    logging.info(
        "Cleanup completed. Total deleted files: %d",
        TotalDeleted
    )

    Report.append("")
    Report.append("Total deleted files: " + str(TotalDeleted))

    # Email Report
    Message = EmailMessage()
    Message["Subject"] = "Duplicate File Cleaner Report"
    Message["From"] = SENDER_EMAIL
    Message["To"] = RECEIVER_EMAIL

    Message.set_content("\n".join(Report))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(Message)

        print("Email report sent successfully.")
        logging.info("Email report sent successfully.")

    except Exception as e:
        print("Email sending failed:", e)
        logging.error("Email sending failed: %s", e)


def main():
    logging.info("Duplicate File Cleaner started.")

    # Run cleanup once when program starts
    DeleteDuplicate("Test")

    # Schedule cleanup every day at 10:00 AM
    schedule.every().day.at("10:00").do(
        DeleteDuplicate, "Test"
    )

    print("Daily cleanup scheduled at 10:00 AM")
    logging.info("Daily cleanup scheduled at 10:00 AM")

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()