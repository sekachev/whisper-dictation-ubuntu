#!/bin/bash
# Toggle script for GNOME Live Dictation

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLIENT_SCRIPT="$DIR/gnome_dictation_client.py"
PID_FILE="/tmp/whisper_dictation.pid"
LOG_FILE="/tmp/whisper_dictation.log"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "Toggling dictation (SIGUSR1 to PID: $PID)..."
        kill -USR1 $PID
        exit 0
    else
        rm "$PID_FILE"
    fi
fi

echo "Starting always-on dictation client (logs in $LOG_FILE)..."
# Set up environment
export LD_LIBRARY_PATH=$(find "$DIR/venv" -name "lib" -type d | tr '\n' ':')
source "$DIR/venv/bin/activate"

# Start client in background and log outputs
# It will start in 'idle' mode by default
python3 "$CLIENT_SCRIPT" > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
