# pylint: disable=missing-docstring, line-too-long

import configparser
import email
import imaplib
import os
import smtplib
import subprocess
import time
import traceback
from email.mime.text import MIMEText

# Initial info from https://copilot.microsoft.com/shares/vS3rk4XggHAfRioMYiqRP

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
    errmsg = None
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
        errmsg = traceback.format_exc()
        print(f"Error sending email: {e}")

    return errmsg


# Function to retrieve an email


def retrieve_email(timestamp):
    errmsg = None
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
                errmsg = "Message not found"
    except Exception as e:  # pylint: disable=broad-except
        print(f"Error retrieving email: {e}")
        errmsg = f"Error fetching email: {traceback.format_exc()}"

    return errmsg


def notify_failure(timestamp, error_message):
    subprocess.run(
        [
            "/usr/local/bin/ntfy",
            "send",
            f"mailtest failed for timestamp {str(timestamp)} ({time.ctime(timestamp)}):\n{error_message}",
        ],
        check=True,
        capture_output=True,
    )


# Main workflow


def main():
    now = time.time()
    if DEBUG_LEVEL > 0:
        print(f"Current timestamp: {time.ctime(now)}")
        print(f"SMTP_SERVER: {SMTP_SERVER}")
        print(f"SMTP_PORT: {SMTP_PORT}")
        print(f"IMAP_SERVER: {IMAP_SERVER}")
        print(f"EMAIL_ADDRESS: {EMAIL_ADDRESS}")

    if result := send_email(now):
        notify_failure(now, f"Send failure: {result}")
    else:
        print("Waiting for email to be sent...")
        time.sleep(30)  # Wait 30 seconds
        print("Retrieving email...")
        if result := retrieve_email(now):
            notify_failure(now, f"Receive failure: {result}")
        else:
            print("Email retrieved successfully")


if __name__ == "__main__":
    main()
