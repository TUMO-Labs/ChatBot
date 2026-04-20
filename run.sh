# -- Setup Flask app --
python3 -m venv venv/
source venv/bin/activate
pip3 install -r requirements.txt
flask run --host=127.0.0.1 --port=5003