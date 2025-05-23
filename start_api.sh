#!/bin/sh
cd "$(dirname "$0")"
echo "Starting Kavak WhatsApp Bot API Server..."
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
