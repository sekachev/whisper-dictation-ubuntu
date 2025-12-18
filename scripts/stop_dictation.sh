#!/bin/bash
# Script to stop the always-on dictation client

PID_FILE="/tmp/whisper_dictation.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "Stopping dictation client (PID: $PID)..."
        kill $PID
        # Wait a bit for graceful cleanup
        sleep 1
        # If still running, force kill
        if ps -p $PID > /dev/null; then
            kill -9 $PID
        fi
    fi
    rm -f "$PID_FILE"
else
    echo "PID file not found. Trying to kill by process name..."
    pkill -f gnome_dictation_client.py
fi

echo "Dictation client stopped."
