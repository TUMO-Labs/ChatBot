#!/bin/bash
# -- Setup Flask app (install dependencies only) --
python3 -m venv venv/
source venv/bin/activate
pip3 install -r requirements.txt

sudo ln -s /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/chatbot

# Test and reload
sudo nginx -t
sudo systemctl reload nginx

# -- Setup systemd service --
sudo cp cv.service /etc/systemd/system/cv.service
sudo systemctl daemon-reload
sudo systemctl enable cv
sudo systemctl restart cv   