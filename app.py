import asyncio
import os
import re
import time
import httpx
import requests
import socketio
from a2wsgi import WSGIMiddleware
from flask import Flask, render_template, jsonify, request
from datetime import datetime

# --- Flask app (HTTP routes) ---
flask_app = Flask(__name__)
flask_app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chatbot-secret')

# --- Socket.IO async server (ASGI) ---
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# --- Telegram config ---
TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
TELEGRAM_CHAT_ID   = os.environ['TELEGRAM_CHAT_ID']
USE_TOPICS         = os.environ.get('USE_TOPICS', '').lower() == 'true'

# session_id -> { username, ip, thread_id }
_sessions: dict[str, dict] = {}
# thread_id -> session_id
_thread_to_session: dict[int, str] = {}
# session_id -> socket sid (None if offline)
_socket_sids: dict[str, str] = {}
# messages queued while client was offline
_pending: dict[str, list[str]] = {}

# Rate limiting for /notify
_notify_last: dict[str, float] = {}
NOTIFY_COOLDOWN = 10


async def _telegram_poll():
    """Background task: polls Telegram getUpdates and pushes replies via WebSocket."""
    offset = None
    print('[POLL] Telegram polling started')
    async with httpx.AsyncClient() as client:
        while True:
            try:
                params = {'timeout': 0, 'allowed_updates': ['message']}
                if offset:
                    params['offset'] = offset

                resp = await client.get(
                    f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates',
                    params=params, timeout=10
                )
                updates = resp.json().get('result', [])

                if updates:
                    offset = updates[-1]['update_id'] + 1

                for update in updates:
                    msg       = update.get('message', {})
                    text      = msg.get('text', '')
                    thread_id = msg.get('message_thread_id')

                    if not text or not thread_id:
                        continue

                    session_id = _thread_to_session.get(thread_id)
                    if not session_id:
                        continue

                    if session_id in _socket_sids:
                        await sio.emit('bot_reply', {'message': text}, room=session_id)
                    else:
                        _pending.setdefault(session_id, []).append(text)
                        print(f'[PENDING] queued for offline session={session_id}')

                if not updates:
                    await asyncio.sleep(1)

            except Exception as e:
                print(f'[POLL ERROR] {e}')
                await asyncio.sleep(5)


@sio.event
async def join(sid, data):
    session_id = data.get('session_id', '')
    await sio.enter_room(sid, session_id)
    _socket_sids[session_id] = sid

    known = session_id in _sessions
    await sio.emit('session_status', {'known': known}, to=sid)
    print(f'[JOIN] session={session_id} known={known}')

    if known:
        for msg in _pending.pop(session_id, []):
            await sio.emit('bot_reply', {'message': msg}, to=sid)


@sio.event
async def disconnect(sid):
    for session_id, stored_sid in list(_socket_sids.items()):
        if stored_sid == sid:
            del _socket_sids[session_id]
            print(f'[DISCONNECT] session={session_id}')
            break


class AppWithStartup:
    def __init__(self):
        self.inner = socketio.ASGIApp(sio, WSGIMiddleware(flask_app))

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan':
            await self._handle_lifespan(scope, receive, send)
            return
        await self.inner(scope, receive, send)

    async def _handle_lifespan(self, scope, receive, send):
        while True:
            event = await receive()
            if event['type'] == 'lifespan.startup':
                asyncio.get_running_loop().create_task(_telegram_poll())
                await send({'type': 'lifespan.startup.complete'})
            elif event['type'] == 'lifespan.shutdown':
                await send({'type': 'lifespan.shutdown.complete'})
                return


app = AppWithStartup()


CONVO_TREE = {
    "start": {
        "bot": "",
        "options": [
            {"text": "💼 Work Experience", "next": "experience"},
            {"text": "🎓 Education",        "next": "education"},
            {"text": "🛠️ Skills",           "next": "skills"},
            {"text": "🚀 Projects",         "next": "projects"},
            {"text": "📬 Contact",          "next": "contact"},
        ]
    },
    "experience": {
        "bot": "I've worked as a Programmer at Tech Company (2022–Present) building Flask dashboards, and as a Junior Frontend Developer at TUMO (2020–2022) crafting responsive UIs.",
        "options": [
            {"text": "🎓 Tell me about education", "next": "education"},
            {"text": "⬅️ Back",                    "next": "start"},
        ]
    },
    "education": {
        "bot": "I hold a B.S. in Computer Science from Tumo Labs (2020–2024), where I focused on full-stack development and software engineering.",
        "options": [
            {"text": "🛠️ What are your skills?", "next": "skills"},
            {"text": "⬅️ Back",                  "next": "start"},
        ]
    },
    "skills": {
        "bot": "My core stack: Python, Flask, JavaScript, React, PostgreSQL, Docker, Git. I'm comfortable across the full stack, from REST APIs to responsive UIs.",
        "options": [
            {"text": "🚀 See my projects", "next": "projects"},
            {"text": "⬅️ Back",            "next": "start"},
        ]
    },
    "projects": {
        "bot": "My notable projects include a Flask analytics dashboard, a React task manager, and this very portfolio chatbot. Want to check my GitHub?",
        "options": [
            {"text": "🔗 Open GitHub", "next": "github"},
            {"text": "⬅️ Back",       "next": "start"},
        ]
    },
    "github": {
        "bot": "You can find all my repositories at github.com/Kristin0. Feel free to star anything you like! 🌟",
        "options": [
            {"text": "📄 Download my CV", "next": "download_cv"},
            {"text": "🏠 Back to Start",  "next": "start"},
        ]
    },
    "download_cv": {
        "bot": "Click here to download my CV → /static/cv.pdf (opens in a new tab)",
        "options": [{"text": "🏠 Back to Start", "next": "start"}]
    },
    "contact": {
        "bot": "You can reach me at kris123kris99@gmail.com or connect on LinkedIn. I usually respond within 24 hours.",
        "options": [{"text": "�� Back to Start", "next": "start"}]
    },
}


@flask_app.route('/')
def index():
    experiences = [
        {"title": "Programmer",               "company": "Tech Company", "year": "2022 - Present", "desc": "Led a team of 5 to develop a Flask-based analytics dashboard."},
        {"title": "Junior Frontend Developer", "company": "TUMO",         "year": "2020 - 2022",    "desc": "Developed 20+ responsive landing pages using modern CSS."},
    ]
    skills = ["Python", "Flask", "JavaScript", "React", "PostgreSQL", "Docker", "Git"]
    projects = [
        {"title": "Online chat application", "desc": "A web-based chat application built with Flask and SQLite, featuring real-time messaging via WebSockets, user authentication, and message encryption.", "tags": ["Python", "Flask", "SQLite", "WebSockets"], "url": "https://github.com/Kristin0/ChatRaspberry"},
        {"title": "Interactive CV Chatbot",  "desc": "This interactive CV chatbot — built with Flask and vanilla JS — that notifies the owner via email when a visitor opens a chat.",                        "tags": ["Python", "Flask", "JavaScript", "SMTP"],       "url": "https://github.com/Kristin0/interactivecv"},
    ]
    return render_template('index.html', experiences=experiences, skills=skills, projects=projects)


@flask_app.route('/chat', methods=['POST'])
def chat():
    next_step = request.json.get('next', 'start')
    return jsonify(CONVO_TREE.get(next_step, CONVO_TREE['start']))


def _sanitize(text: str, max_len: int = 200) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[\x00-\x1f\x7f]', '', text)
    return text.strip()[:max_len]


def _get_country(ip: str) -> str:
    if ip in ('127.0.0.1', 'localhost'):
        return '🏠 localhost'
    try:
        r = requests.get(f'http://ip-api.com/json/{ip}?fields=country,countryCode', timeout=3)
        data = r.json()
        if data.get('country'):
            return f'{data["country"]} ({data["countryCode"]})'
    except Exception:
        pass
    return 'Unknown'


def _tg_send(text: str, thread_id: int = None) -> None:
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': text}
    if thread_id:
        payload['message_thread_id'] = thread_id
    requests.post(f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage', json=payload, timeout=5)


@flask_app.route('/notify', methods=['POST'])
def notify():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

    now = time.time()
    if ip != '127.0.0.1' and now - _notify_last.get(ip, 0) < NOTIFY_COOLDOWN:
        return jsonify({'status': 'rate_limited'}), 429
    _notify_last[ip] = now

    data       = request.json
    username   = _sanitize(data.get('username', 'Anonymous'))
    message    = _sanitize(data.get('message', ''))
    session_id = data.get('session_id', '')
    visited_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    thread_id = None
    if USE_TOPICS:
        try:
            r = requests.post(
                f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/createForumTopic',
                json={'chat_id': TELEGRAM_CHAT_ID, 'name': f'Visitor {username}'[:128]}, timeout=5
            )
            result = r.json()
            if result.get('ok'):
                thread_id = result['result']['message_thread_id']
        except Exception as e:
            print(f'[TOPIC ERROR] {e}')

    country = _get_country(ip)
    _sessions[session_id] = {'username': username, 'ip': ip, 'thread_id': thread_id}
    if thread_id:
        _thread_to_session[thread_id] = session_id

    text = (
        f'💬 New chat visitor!\n\n'
        f'👤 Name: {username}\n'
        f'🌐 IP: {ip}\n'
        f'🗺️ Country: {country}\n'
        f'✉️ Message: {message}\n'
        f'🕐 Time: {visited_at}\n\n'
        f'Reply in this topic to respond.'
    )
    try:
        _tg_send(text, thread_id=thread_id)
        return jsonify({'status': 'ok', 'session_id': session_id})
    except Exception as e:
        print(f'[NOTIFY ERROR] {e}')
        return jsonify({'status': 'error', 'detail': str(e)}), 500


@flask_app.route('/send-message', methods=['POST'])
def send_message():
    data       = request.json
    session_id = _sanitize(data.get('session_id', ''), 64)
    message    = _sanitize(data.get('message', ''))
    session    = _sessions.get(session_id)
    if not session or not message:
        return jsonify({'status': 'ignored'}), 200
    try:
        _tg_send(f'💬 [{session["username"]}]: {message}', thread_id=session.get('thread_id'))
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'detail': str(e)}), 500
