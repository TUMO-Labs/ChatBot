from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True)