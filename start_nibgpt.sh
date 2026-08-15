#!/bin/bash

PROJECT_DIR="/root/projects/nibgpt"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
LOG_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/pids"

mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

echo "========================================"
echo "        Starting NIBGPT Platform"
echo "========================================"

# Stop previously running development processes
if [ -f "$PID_DIR/backend.pid" ]; then
    OLD_BACKEND_PID=$(cat "$PID_DIR/backend.pid")

    if kill -0 "$OLD_BACKEND_PID" 2>/dev/null; then
        echo "Stopping previous backend process..."
        kill "$OLD_BACKEND_PID"
    fi

    rm -f "$PID_DIR/backend.pid"
fi

if [ -f "$PID_DIR/frontend.pid" ]; then
    OLD_FRONTEND_PID=$(cat "$PID_DIR/frontend.pid")

    if kill -0 "$OLD_FRONTEND_PID" 2>/dev/null; then
        echo "Stopping previous frontend process..."
        kill "$OLD_FRONTEND_PID"
    fi

    rm -f "$PID_DIR/frontend.pid"
fi

# Start backend
echo "Starting FastAPI backend..."

cd "$BACKEND_DIR" || exit 1

nohup "$BACKEND_DIR/venv/bin/python" -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    > "$LOG_DIR/backend.log" 2>&1 &

BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_DIR/backend.pid"

sleep 3

if kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "Backend started successfully."
else
    echo "Backend failed to start."
    echo "Check: $LOG_DIR/backend.log"
    exit 1
fi

# Start frontend
echo "Starting React frontend..."

cd "$FRONTEND_DIR" || exit 1

nohup npm run dev -- --host 0.0.0.0 \
    > "$LOG_DIR/frontend.log" 2>&1 &

FRONTEND_PID=$!
echo "$FRONTEND_PID" > "$PID_DIR/frontend.pid"

sleep 3

if kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo "Frontend started successfully."
else
    echo "Frontend failed to start."
    echo "Check: $LOG_DIR/frontend.log"
    exit 1
fi

echo ""
echo "========================================"
echo "          NIBGPT is running"
echo "========================================"
echo "Frontend: http://172.24.0.13:5173"
echo "Backend:  http://172.24.0.13:8000"
echo "API Docs: http://172.24.0.13:8000/docs"
echo ""
echo "Backend log:  $LOG_DIR/backend.log"
echo "Frontend log: $LOG_DIR/frontend.log"
echo "========================================"
