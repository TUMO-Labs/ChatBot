#!/bin/bash
# -- Setup and run Flask app with Gunicorn --
python3 -m venv venv/
source venv/bin/activate
pip3 install -r requirements.txt
gunicorn --worker-class gthread --workers 1 --threads 4 --bind 127.0.0.1:5003 app:app


# Copy to nginx sites
sudo cp nginx.conf /etc/nginx/sites-available/chatbot
sudo ln -s /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/chatbot

# Test and reload
sudo nginx -t
sudo systemctl reload nginx