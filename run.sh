#!/bin/bash
set -e

# -- Install system dependencies --
sudo apt update
sudo apt install -y python3-venv python3-pip nginx

# -- Setup Python venv --
python3 -m venv venv/
source venv/bin/activate
pip3 install -r requirements.txt

# -- Setup Nginx --
sudo rm -f /etc/nginx/sites-enabled/default
sudo rm -f /etc/nginx/sites-enabled/cv.conf
sudo cp nginx/cv.conf /etc/nginx/sites-available/cv.conf
sudo ln -s /etc/nginx/sites-available/cv.conf /etc/nginx/sites-enabled/cv.conf
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

# -- Setup systemd service --
sudo cp cv.service /etc/systemd/system/cv.service
sudo systemctl daemon-reload
sudo systemctl enable cv
sudo systemctl restart cv
