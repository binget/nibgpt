#!/bin/bash

PROJECT_DIR="/root/projects/nibgpt"
PID_DIR="$PROJECT_DIR/pids"

echo "Stopping NIBGPT..."

if [ -f "$PID_DIR/backend.pid" ]; then
    BACKEND_PID=$(cat "$PID_DIR/backend.pid")

    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID"
        echo "Backend stopped."
    fi

    rm -f "$PID_DIR/backend.pid"
else
    pkill -f "uvicorn app.main:app" 2>/dev/null
fi

if [ -f "$PID_DIR/frontend.pid" ]; then
    FRONTEND_PID=$(cat "$PID_DIR/frontend.pid")

    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID"
        echo "Frontend stopped."
    fi

    rm -f "$PID_DIR/frontend.pid"
else
    pkill -f "vite" 2>/dev/null
fi

echo "NIBGPT stopped."
