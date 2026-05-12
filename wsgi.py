import app as app_module
from app import app, socketio, _telegram_poll

# Prevent double-start
app_module._poll_started = True

# Start Telegram polling once when the worker process starts
socketio.start_background_task(_telegram_poll)
print('[WSGI] Telegram polling started at worker init')
