from flask import Flask, render_template, jsonify, request
import os
import re
import time
import uuid
import requests
from datetime import datetime

app = Flask(__name__)

# --- Telegram Configuration (set via environment variables) ---
TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
TELEGRAM_CHAT_ID   = os.environ['TELEGRAM_CHAT_ID']   # your personal chat ID

# --- Rate limiting: ip -> last notify timestamp ---
_notify_last: dict[str, float] = {}
NOTIFY_COOLDOWN = 60  # seconds

# --- Session store: session_id -> { username, ip, reply_queue[] } ---
_sessions: dict[str, dict] = {}

CONVO_TREE = {
    "start": {
        "bot": "Hi! I'm your virtual assistant. How can I help you today?",
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
        "options": [{"text": "🏠 Back to Start", "next": "start"}]
    },
}

@app.route('/')
def index():
    experience_data = [
        {
            "title": "Programmer",
            "company": "Tech Company",
            "year": "2022 - Present",
            "desc": "Led a team of 5 to develop a Flask-based analytics dashboard."
        },
        {
            "title": "Junior Frontend Developer",
            "company": "TUMO",
            "year": "2020 - 2022",
            "desc": "Developed 20+ responsive landing pages using modern CSS."
        }
    ]
    skills = ["Python", "Flask", "JavaScript", "React", "PostgreSQL", "Docker", "Git"]
    projects = [
        {
            "title": "Online chat application",
            "desc": "A web-based chat application built with Flask and SQLite, featuring real-time messaging via WebSockets, user authentication, and message encryption.",
            "tags": ["Python", "Flask", "SQLite", "WebSockets"],
            "url": "https://github.com/Kristin0/ChatRaspberry"
        },
        {
            "title": "Interactive CV Chatbot",
            "desc": "This interactive CV chatbot — built with Flask and vanilla JS — that notifies the owner via email when a visitor opens a chat.",
            "tags": ["Python", "Flask", "JavaScript", "SMTP"],
            "url": "https://github.com/Kristin0/interactivecv"
        },
    ]
    return render_template('index.html', experiences=experience_data, skills=skills, projects=projects)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    next_step = data.get('next', 'start')
    response = CONVO_TREE.get(next_step, CONVO_TREE['start'])
    return jsonify(response)

def _sanitize(text: str, max_len: int = 200) -> str:
    """Strip HTML/control characters and truncate."""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[\x00-\x1f\x7f]', '', text)
    return text.strip()[:max_len]

def _telegram_send(text: str) -> None:
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': text}, timeout=5)

@app.route('/notify', methods=['POST'])
def notify():
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

    # Rate limiting
    now = time.time()
    if now - _notify_last.get(ip_address, 0) < NOTIFY_COOLDOWN:
        return jsonify({'status': 'rate_limited'}), 429
    _notify_last[ip_address] = now

    data       = request.json
    username   = _sanitize(data.get('username', 'Anonymous'))
    message    = _sanitize(data.get('message', ''))
    session_id = data.get('session_id', '')
    visited_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Store session
    _sessions[session_id] = {'username': username, 'ip': ip_address, 'replies': []}

    text = (
        f'💬 New chat visitor!\n\n'
        f'👤 Name: {username}\n'
        f'🌐 IP: {ip_address}\n'
        f'✉️ Message: {message}\n'
        f'🕐 Time: {visited_at}\n\n'
        f'Reply with:\n/reply {session_id} your message here'
    )

    try:
        _telegram_send(text)
        return jsonify({'status': 'ok', 'session_id': session_id})
    except Exception as e:
        print(f'[Telegram Error] {e}')
        return jsonify({'status': 'error', 'detail': str(e)}), 500

@app.route('/send-message', methods=['POST'])
def send_message():
    """Visitor sends a free-text message → forwarded to Telegram."""
    data       = request.json
    session_id = _sanitize(data.get('session_id', ''), 64)
    message    = _sanitize(data.get('message', ''))
    session    = _sessions.get(session_id)
    if not session or not message:
        return jsonify({'status': 'ignored'}), 200

    text = f'💬 [{session["username"]}]: {message}\n\nReply: /reply {session_id} your message'
    try:
        _telegram_send(text)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'detail': str(e)}), 500

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    """Receive messages from Telegram and route to the right visitor session."""
    data = request.json
    message = data.get('message', {})
    text = message.get('text', '')

    # Format: /reply <session_id> <message text>
    if text.startswith('/reply '):
        parts = text[7:].split(' ', 1)
        if len(parts) == 2:
            session_id, reply = parts
            session = _sessions.get(session_id)
            if session:
                session['replies'].append(reply)

    return jsonify({'ok': True})

@app.route('/messages/<session_id>', methods=['GET'])
def get_messages(session_id):
    """Visitor polls this to get replies from the owner."""
    session = _sessions.get(session_id)
    if not session:
        return jsonify({'replies': []})
    replies = session['replies'].copy()
    session['replies'].clear()
    return jsonify({'replies': replies})


if __name__ == '__main__':
    app.run(debug=True)