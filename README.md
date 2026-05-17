# CV Chatbot

An interactive portfolio chatbot built with Flask, Socket.IO, and Telegram. Visitors can browse your CV through a conversation tree and send live messages — you receive them in Telegram and can reply in real time directly to the visitor's browser.

## Features

- Interactive chat widget with a guided conversation tree (work experience, education, skills, projects)
- Visitor name prompt before the chat starts
- Telegram notification on every new chat session with visitor name, IP, and country
- **Live two-way messaging**: reply in a Telegram forum topic → message appears instantly in the visitor's browser via WebSocket
- Pending message queue: messages sent while the visitor is offline are delivered on reconnect
- Rate limiting on notifications (per IP)

## Architecture

```
Browser
  │
  ├─── HTTP (GET /, POST /chat, /notify, /send-message)
  │         └── Flask (WSGI routes)
  │
  └─── WebSocket (Socket.IO)
            └── python-socketio AsyncServer (ASGI)

Both are served by a single uvicorn process via ASGI.
Flask is wrapped with WSGIMiddleware (a2wsgi) to fit inside the ASGI stack.

Background task (_telegram_poll):
  └── Runs as an asyncio task started on lifespan.startup
      Polls Telegram getUpdates (short-poll, timeout=0)
      Routes replies: thread_id → session_id → WebSocket emit
```

### Tech stack

| Layer | Technology |
|---|---|
| HTTP server | **uvicorn** (ASGI) |
| HTTP routes | **Flask** (wrapped via `WSGIMiddleware`) |
| WebSocket | **python-socketio** `AsyncServer` (ASGI mode) |
| Async HTTP client | **httpx** (Telegram polling) |
| Sync HTTP client | **requests** (Telegram send, ip-api.com) |
| Telegram adapter | **a2wsgi** `WSGIMiddleware` |

### WebSocket transport

Socket.IO first performs an HTTP handshake (long-polling), then upgrades to a persistent WebSocket connection. The client is configured with:

```js
io({ transports: ['polling', 'websocket'], upgrade: true })
```

`polling` is used only for the initial handshake. All subsequent communication goes over WebSocket. Keeping `polling` as a fallback ensures the chat works even in networks that block WebSocket.

### Telegram polling

The background task uses `timeout=0` (short-poll) — Telegram responds immediately with any pending updates. If there are no updates, the task sleeps for 1 second before polling again. This gives a maximum message delivery latency of ~1 second, while keeping only one persistent HTTP connection to Telegram.

> ⚠️ Only one instance of the app should run at a time. Running both a local instance and a production server simultaneously causes a `409 Conflict` from Telegram (`getUpdates` can only be held by one client).

### In-memory state

| Dict | Key → Value | Purpose |
|---|---|---|
| `_sessions` | `session_id → {username, ip, thread_id}` | Visitor data |
| `_thread_to_session` | `thread_id → session_id` | Route Telegram reply to correct session |
| `_socket_sids` | `session_id → socket sid` | Know if visitor is currently online |
| `_pending` | `session_id → [messages]` | Queue for offline visitors |

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
USE_TOPICS=true
SECRET_KEY=your_secret_key
```

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | ID of the Telegram group/supergroup |
| `USE_TOPICS` | Set to `true` to create a separate forum topic per visitor |
| `SECRET_KEY` | Flask secret key |

> `USE_TOPICS=true` requires the Telegram group to have **Topics** (forum mode) enabled.

## Running

```bash
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)
uvicorn asgi:app --host 127.0.0.1 --port 5003
```

## Production (systemd)

See `cv.service` for a ready-made systemd unit. Deploy with:

```bash
sudo cp cv.service /etc/systemd/system/cv.service
sudo systemctl daemon-reload
sudo systemctl enable cv
sudo systemctl start cv
```
