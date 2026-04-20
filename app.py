from flask import Flask, render_template, jsonify, request
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# --- Gmail Configuration (set via environment variables) ---
EMAIL_SENDER    = os.environ['NOTIFY_EMAIL_SENDER']
EMAIL_PASSWORD  = os.environ['NOTIFY_EMAIL_PASSWORD']
EMAIL_RECIPIENT = os.environ['NOTIFY_EMAIL_RECIPIENT']
SMTP_HOST       = 'smtp.gmail.com'
SMTP_PORT       = 587

CONVO_TREE = {
    "start": {
        "bot": "Hi! I'm your virtual assistant. How can I help you today?",
        "options": [
            {"text": "🚀 View Projects", "next": "projects"},
            {"text": "📬 Contact Info", "next": "contact"}
        ]
    },
    "projects": {
        "bot": "I specialize in Flask and React. This portfolio is built with Python! Want to see my GitHub?",
        "options": [
            {"text": "🔗 Yes, take me there", "next": "github"},
            {"text": "⬅️ Back", "next": "start"}
        ]
    },
    "github": {
        "bot": "You can find my repositories at github.com/yourusername. Anything else?",
        "options": [{"text": "Back to Start", "next": "start"}]
    },
    "contact": {
        "bot": "You can reach my human creator at dev@example.com.",
        "options": [{"text": "Start Over", "next": "start"}]
    }
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
    
    return render_template('index.html', experiences=experience_data, skills=skills)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    next_step = data.get('next', 'start')
    response = CONVO_TREE.get(next_step, CONVO_TREE['start'])
    return jsonify(response)

@app.route('/notify', methods=['POST'])
def notify():
    data       = request.json
    print(f'[NOTIFY] Received: {data}')
    username   = data.get('username', 'Anonymous')
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    message    = data.get('message', '')

    subject = f'New Chat Session from {username}'
    body = (
        f'A new visitor opened the chat.\n\n'
        f'Username : {username}\n'
        f'IP Address: {ip_address}\n'
        f'First Message: {message}\n'
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