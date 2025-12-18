# Whisper Dictation for Ubuntu (GNOME/Wayland)

This project turns [WhisperLive](https://github.com/CollaboraOnline/WhisperLive) into a full-fledged system service for Ubuntu with global dictation support via a hotkey.

## Features
- **Global Dictation**: Works in any application (Chrome, Telegram, IDE).
- **Live Output**: Text is typed immediately as you speak.
- **Background Loading**: The server keeps the model in memory for instant response.
- **Always-on Client**: Minimal startup delay, status indicated via a system tray icon.
- **System Tray Integration**:
  - **Grey Circle**: Standby mode.
  - **Red Circle**: Recording mode.

## Installation

```bash
git clone https://github.com/sekachev/whisper-dictation-ubuntu.git
cd whisper-dictation-ubuntu
chmod +x install.sh
./install.sh
```

## Hotkey Configuration

1. Open **Settings** -> **Keyboard** -> **View and Customize Shortcuts**.
2. Select **Custom Shortcuts** at the bottom.
3. Click **+** and enter:
   - **Name**: Whisper Dictation
   - **Command**: `/bin/bash /path/to/project/WhisperLive/scripts/toggle_dictation.sh`
   - **Shortcut**: Any convenient key (e.g., `Super + D`).

## Service Management

The transcription server runs as a system service:

- Check status: `sudo systemctl status whisper-server`
- View logs (real-time): `journalctl -u whisper-server -f`
- Restart: `sudo systemctl restart whisper-server`

To completely stop the tray client:
- Run `./scripts/stop_dictation.sh`

## Technical Details
- Uses the `evdev` library for hardware-level key simulation (bypassing Wayland restrictions).
- Uses clipboard paste (`Ctrl+V`) for fast and reliable text insertion in browsers like Chrome.
- Default model: `turbo`.
- Status icon is drawn programmatically (no external asset files required).

---
*Based on the [WhisperLive](https://github.com/CollaboraOnline/WhisperLive) repository.*
