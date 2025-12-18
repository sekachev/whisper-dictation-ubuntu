#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting Whisper Dictation Ubuntu installation..."

# 1. Clone original WhisperLive if not exists
if [ ! -d "WhisperLive" ]; then
    echo "📥 Cloning original WhisperLive repository..."
    git clone https://github.com/CollaboraOnline/WhisperLive.git
fi

# 2. Apply our patches
echo "🛠 Applying custom patches..."
cp patches/run_server.py WhisperLive/
cp patches/setup.py WhisperLive/
cp patches/whisper_live/server.py WhisperLive/whisper_live/server.py
cp scripts/gnome_dictation_client.py WhisperLive/
cp scripts/toggle_dictation.sh WhisperLive/

# 3. Create virtual environment and install dependencies
cd WhisperLive
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🔌 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
# Install the modified package in editable mode or just install requirements
pip install -e .
pip install pyperclip evdev
deactivate
cd ..

# 4. Setup uinput permissions for virtual keyboard
echo "⌨ Setting up uinput permissions..."
if [ ! -f "/etc/udev/rules.d/99-uinput.rules" ]; then
    echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/99-uinput.rules
    sudo udevadm control --reload-rules
    sudo udevadm trigger
fi
sudo usermod -aG input $USER

# 5. Configure and Install Systemd Service
echo "⚙ Configuring systemd services..."
INSTALL_DIR=$(pwd)/WhisperLive
USER_NAME=$USER

# Patch service file with current paths and user
sed -e "s|/home/sekachev/Documents/whipser/WhisperLive|$INSTALL_DIR|g" \
    -e "s|User=sekachev|User=$USER_NAME|g" \
    services/whisper-server.service > whisper-server.service.tmp

sudo cp whisper-server.service.tmp /etc/systemd/system/whisper-server.service
rm whisper-server.service.tmp

# Optional: ydotoold if needed (though gnome_dictation_client uses evdev now)
if [ -f "services/ydotoold.service" ]; then
    sudo cp services/ydotoold.service /etc/systemd/system/
fi

sudo systemctl daemon-reload
echo "✅ Installation complete!"
echo "-------------------------------------------------------"
echo "To start the server: sudo systemctl start whisper-server"
echo "To enable on boot:   sudo systemctl enable whisper-server"
echo ""
echo "Hotkey setup command:"
echo "/bin/bash $INSTALL_DIR/toggle_dictation.sh"
echo "-------------------------------------------------------"
