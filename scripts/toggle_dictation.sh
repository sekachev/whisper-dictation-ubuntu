#!/bin/bash
# Toggle script for GNOME Live Dictation

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLIENT_SCRIPT="$DIR/gnome_dictation_client.py"
PID_FILE="/tmp/whisper_dictation.pid"
LOG_FILE="/tmp/whisper_dictation.log"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "Stopping dictation (PID: $PID)..."
        kill $PID
        rm "$PID_FILE"
        exit 0
    else
        rm "$PID_FILE"
    fi
fi

echo "Starting dictation (logs in $LOG_FILE)..."
# Set up environment
export LD_LIBRARY_PATH=$(find "$DIR/venv" -name "lib" -type d | tr '\n' ':')
source "$DIR/venv/bin/activate"

# Start client in background and log outputs
python3 "$CLIENT_SCRIPT" > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
