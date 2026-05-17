# ASGI entrypoint for uvicorn
# Run: uvicorn asgi:app --host 127.0.0.1 --port 5003 --workers 1
from app import app
