from flask import Flask, render_template, jsonify, request
import smtplib
import os
import re
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# --- Gmail Configuration (set via environment variables) ---
EMAIL_SENDER    = os.environ['NOTIFY_EMAIL_SENDER']
EMAIL_PASSWORD  = os.environ['NOTIFY_EMAIL_PASSWORD']
EMAIL_RECIPIENT = os.environ['NOTIFY_EMAIL_RECIPIENT']
SMTP_HOST       = 'smtp.gmail.com'
SMTP_PORT       = 587

# --- Rate limiting: ip -> last notify timestamp ---
_notify_last: dict[str, float] = {}
NOTIFY_COOLDOWN = 60  # seconds

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
    text = re.sub(r'<[^>]+>', '', text)          # strip HTML tags
    text = re.sub(r'[\x00-\x1f\x7f]', '', text) # strip control chars
    return text.strip()[:max_len]

@app.route('/notify', methods=['POST'])
def notify():
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

    # Rate limiting
    now = time.time()
    if now - _notify_last.get(ip_address, 0) < NOTIFY_COOLDOWN:
        return jsonify({'status': 'rate_limited'}), 429
    _notify_last[ip_address] = now

    data     = request.json
    print(f'[NOTIFY] Received: {data}')
    username = _sanitize(data.get('username', 'Anonymous'))
    message  = _sanitize(data.get('message', ''))
    visited_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    subject = f'New Chat Session from {username}'
    body = (
        f'A new visitor opened the chat.\n\n'
        f'Username   : {username}\n'
        f'IP Address : {ip_address}\n'
        f'First Message: {message}\n'
        f'Time       : {visited_at}\n'
    )

    try:
        msg = MIMEMultipart()
        msg['From']    = EMAIL_SENDER
        msg['To']      = EMAIL_RECIPIENT
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())

        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f'[Email Error] {e}')
        return jsonify({'status': 'error', 'detail': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)