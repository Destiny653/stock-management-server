#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing requirements..."
pip install -r requirements.txt

echo "Starting server..."
# uvicorn main:app --reload --host [IP_ADDRESS] --port 8000 --ssl-keyfile ./ssl/key.pem --ssl-certfile ./ssl/cert.pem
uvicorn main:app --reload