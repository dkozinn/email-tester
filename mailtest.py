# pylint: disable=missing-docstring

import configparser
import email
import imaplib
import os
import smtplib
import subprocess
import time
import traceback
from email.mime.text import MIMEText

# https://copilot.microsoft.com/shares/vS3rk4XggHAfRioMYiqRP

CONF_FILE = "mailtest.ini"

config = configparser.ConfigParser()
config.read([CONF_FILE, os.path.expanduser(f"~/.config/{CONF_FILE}")])

SMTP_SERVER = config["EMAIL"]["SMTP_SERVER"]
SMTP_PORT = int(config["EMAIL"]["SMTP_PORT"])
IMAP_SERVER = config["EMAIL"]["IMAP_SERVER"]
EMAIL_ADDRESS = config["EMAIL"]["EMAIL_ADDRESS"]
EMAIL_PASSWORD = config["EMAIL"]["EMAIL_PASSWORD"]
DEBUG_LEVEL = 4 if config["EMAIL"].getboolean("DEBUG", False) else 0

# Function to send an email


def send_email(timestamp):
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.set_debuglevel(DEBUG_LEVEL)
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            msg = MIMEText(
                f"This is a test email sent via Python at {time.ctime(timestamp)}."
            )
            msg["From"] = EMAIL_ADDRESS
            msg["To"] = EMAIL_ADDRESS  # Sending to the same address
            msg["Subject"] = "Test Email " + str(timestamp)
            server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, msg.as_string())
            print("Email sent successfully.")
    except Exception as e:  # pylint: disable=broad-except
        subprocess.run(
            [
                "/usr/local/bin/ntfy",
                "send",
                f"mailtest send failed for timestamp {str(timestamp)}:\n{traceback.format_exc()}",
            ],
            check=True,
            capture_output=True,
        )
        print(f"Error sending email: {e}")


# Function to retrieve an email


def retrieve_email(timestamp):
    try:
        with imaplib.IMAP4_SSL(IMAP_SERVER) as mail:
            mail.debug = DEBUG_LEVEL
            mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            mail.select("inbox")  # Select the mailbox
            # Search for emails with "Test Email" in the subject
            result, data = mail.search(
                None, '(SUBJECT "Test Email ' + str(timestamp) + '")'
            )
            if result == "OK" and len(data[0]) > 0:
                for num in data[0].split():
                    result, msg_data = mail.fetch(num, "(RFC822)")
                    if result == "OK":
                        msg = email.message_from_bytes(msg_data[0][1])
                        print("Email retrieved:")
                        print(f"From: {msg['From']}")
                        print(f"Subject: {msg['Subject']}")
                        print(f"Body: {msg.get_payload(decode=True).decode()}")
                        # Mark the email for deletion
                        mail.store(num, "+FLAGS", "\\Deleted")
                        mail.expunge()
                        print("Email deleted.")
                        break
            else:
                subprocess.run(
                    [
                        "/usr/local/bin/ntfy",
                        "send",
                        f"mailtest receive failed for timestamp {str(timestamp)}: Message not found"
                    ],
                    check=True,
                    capture_output=True,
                )
    except Exception as e:  # pylint: disable=broad-except
        subprocess.run(
            [
                "/usr/local/bin/ntfy",
                "send",
                f"mailtest receive failed for timestamp {str(timestamp)}:\n{traceback.format_exc()}"
            ],
            check=True,
            capture_output=True,
        )
        print(f"Error retrieving email: {e}")


# Main workflow


if __name__ == "__main__":
    now = time.time()
    send_email(now)
    time.sleep(30)  # Wait 30 seconds
    retrieve_email(now)
