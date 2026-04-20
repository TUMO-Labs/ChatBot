# ChatBot

A Flask-based portfolio chatbot that notifies you by email whenever a visitor opens the chat — including their name, IP address, and first message.

## Features

- Interactive chat widget with a conversation tree
- Visitor name prompt before the chat starts
- Email notification sent to your Gmail on every new chat session

## Setup

```bash
python3 -m venv venv/
source venv/bin/activate
pip3 install -r requirements.txt
```

## Running

Set the required email environment variables and start the server:

```bash
NOTIFY_EMAIL_SENDER="you@gmail.com" \
NOTIFY_EMAIL_PASSWORD="your_app_password" \
NOTIFY_EMAIL_RECIPIENT="you@gmail.com" \
./run.sh
```

| Variable | Description |
|---|---|
| `NOTIFY_EMAIL_SENDER` | Gmail address used to **send** the notification |
| `NOTIFY_EMAIL_PASSWORD` | [Gmail App Password](https://myaccount.google.com/apppasswords) (16 chars, not your regular password) |
| `NOTIFY_EMAIL_RECIPIENT` | Gmail address that **receives** the notification |

> ⚠️ Gmail requires **2-Step Verification** to be enabled before you can create an App Password.

## Email Notification Format

```
Subject: New Chat Session from <username>

A new visitor opened the chat.

Username  : John
IP Address: 192.168.1.1
First Message: Opened chat
```
