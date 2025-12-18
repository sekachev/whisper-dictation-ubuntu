import os
import sys
import time
import pyperclip
import evdev
from evdev import UInput, ecodes as e
import threading
import pystray
from PIL import Image, ImageDraw
from whisper_live.client import TranscriptionClient
import signal



# Virtual input device (keyboard) setup
# This creates a "hardware" keyboard at the kernel level
cap = {
    e.EV_KEY: [
        e.KEY_BACKSPACE, e.KEY_LEFTCTRL, e.KEY_V, 
        e.KEY_LEFTSHIFT, e.KEY_INSERT, e.KEY_A
    ]
}

class GNOMELiveTypist:
    def __init__(self):
        try:
            self.ui = UInput(cap, name='Whisper-Virtual-Keyboard')
            print("[INFO]: Virtual Keyboard created successfully via evdev")
        except Exception as ex:
            print(f"[ERROR]: Failed to create virtual keyboard: {ex}")
            sys.exit(1)
            
        self.currently_typed = ""
        self.last_locked_time = 0
        self.is_list_mode = False

    def press_keys(self, keys):
        # Press all keys in the list
        for k in keys:
            self.ui.write(e.EV_KEY, k, 1)
        self.ui.syn()
        # Release them in reverse order
        for k in reversed(keys):
            self.ui.write(e.EV_KEY, k, 0)
        self.ui.syn()

    def backspace(self, count):
        if count <= 0:
            return
        # For a small number, use normal backspace
        if count < 10:
            for _ in range(count):
                self.press_keys([e.KEY_BACKSPACE])
                time.sleep(0.005)
        else:
            # For a large number, also use backspace, but slightly faster
            for _ in range(count):
                self.press_keys([e.KEY_BACKSPACE])
                time.sleep(0.002)

    def clear_all(self):
        # This function is no longer used to prevent full field clearing
        self.press_keys([e.KEY_LEFTCTRL, e.KEY_A])
        time.sleep(0.02)
        self.press_keys([e.KEY_BACKSPACE])
        time.sleep(0.02)

    def paste_text(self, text):
        if not text:
            return
        # Copy text to clipboard
        pyperclip.copy(text)
        time.sleep(0.05) # Pause for Chrome
        
        # Press hardware Ctrl + V
        self.press_keys([e.KEY_LEFTCTRL, e.KEY_V])
        time.sleep(0.02)

    def on_transcription(self, full_text, segments):
        # List of hallucinations
        hallucinations = [
            "продолжение следует", 
            "продолжение следует...",
            "благодарю за внимание",
            "спасибо за просмотр",
            "подписывайтесь на канал",
            "thanks for watching",
            "subtitles by",
            "субтитры сделал dimatorzok",
            "субтитры подготовил dimatorzok",
            "субтитры сделал",
            "субтитры подготовил",
            "to be continued",
            "thank you for watching",
            "subscribe to the channel"
        ]
        
        # Control commands
        list_start_cmds = ["новый список", "начать список", "start list", "new list"]
        list_end_cmds = ["конец списка", "закончить список", "end list", "stop list"]
        enter_cmds = ["новая строка", "enter", "энтер", "перенос строки", "new line"]

        def process_text_part(txt, list_mode_state):
            t_lower = txt.lower().strip().rstrip(".")
            if t_lower in list_start_cmds:
                return "\n- ", True
            if t_lower in list_end_cmds:
                return "\n", False
            if t_lower in enter_cmds:
                return ("\n- " if list_mode_state else "\n"), list_mode_state
            return txt, list_mode_state

        # 1. Filter segments for hallucinations
        valid_segments = []
        for seg in segments:
            t = seg["text"].strip()
            if t.lower() in hallucinations:
                print(f"[DEBUG]: Hallucination ignored: '{t}'")
                continue
            valid_segments.append(seg)
            
        if not valid_segments:
            return

        # 2. Determine stability window boundary
        current_max_time = float(valid_segments[-1].get("end", 0))
        
        lock_until_idx = 0
        for i, seg in enumerate(valid_segments):
            end_t = float(seg.get("end", 0))
            if end_t <= self.last_locked_time:
                lock_until_idx = i + 1
                continue
                
            if seg.get("completed", False) and end_t < (current_max_time - 3.0):
                lock_until_idx = i + 1
                
                # Segment text and its transformation to "concrete"
                text_raw = seg["text"].strip()
                text_transformed, next_list_mode = process_text_part(text_raw, self.is_list_mode)
                
                # Look for this text at the beginning of our buffer and cut it off
                if self.currently_typed.startswith(text_transformed):
                    self.currently_typed = self.currently_typed[len(text_transformed):].lstrip(" ")
                    self.last_locked_time = end_t
                    self.is_list_mode = next_list_mode
                    print(f"[DEBUG]: Locking: '{text_transformed.replace(chr(10), ' [ENT] ')}'. Mode: {self.is_list_mode}")
                else:
                    self.currently_typed = ""
                    self.last_locked_time = end_t
                    self.is_list_mode = next_list_mode
                    print(f"[DEBUG]: Desync in locking, reset baseline. Mode: {self.is_list_mode}")
            else:
                break
        
        # 3. Form active text considering commands
        current_active_mode = self.is_list_mode
        active_parts = []
        for s in valid_segments[lock_until_idx:]:
            txt_raw = s["text"].strip()
            txt_transformed, current_active_mode = process_text_part(txt_raw, current_active_mode)
            active_parts.append(txt_transformed)
        
        # Smart join
        target_text = ""
        for part in active_parts:
            if part.startswith("\n"):
                target_text += part
            else:
                if target_text and not target_text.endswith(("\n", "- ", " ")):
                    target_text += " "
                target_text += part
        
        if not target_text and not self.currently_typed:
            return
            
        if target_text == self.currently_typed:
            return

        # 4. Differential typing
        common_prefix_len = 0
        min_len = min(len(target_text), len(self.currently_typed))
        for i in range(min_len):
            if target_text[i] == self.currently_typed[i]:
                common_prefix_len += 1
            else:
                break
        
        chars_to_delete = len(self.currently_typed) - common_prefix_len
        text_to_add = target_text[common_prefix_len:]
        
        if chars_to_delete > 0 or text_to_add:
            print(f"[DEBUG]: Diff - Del: {chars_to_delete}, Add: '{text_to_add.replace(chr(10), ' [ENT] ')}'")

        if chars_to_delete > 0:
            self.backspace(chars_to_delete)
        
        if text_to_add:
            self.paste_text(text_to_add)

        self.currently_typed = target_text

class DictationManager:
    def __init__(self):
        self.typist = GNOMELiveTypist()
        self.recording_active = False
        self.client = None
        self.client_thread = None
        self.current_lang = "ru" # Default to Russian
        
        # Create icons programmatically - simple solid circles
        self.img_idle = self._create_simple_circle("grey")
        self.img_active = self._create_simple_circle("#ff0000")

        # Menu is removed as requested due to glitches in the environment
        self.icon = pystray.Icon("whisper_live", self.img_idle, "Whisper Dictation")
        
    def _create_simple_circle(self, color):
        width, height = 64, 64
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        # Clean solid circle, no outline
        padding = 6
        box = [padding, padding, width - padding, height - padding]
        draw.ellipse(box, fill=color)
        return image

    def toggle(self, signum=None, frame=None):
        # This is the signal handler for SIGUSR1
        if self.recording_active:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if self.recording_active: return
        print(f"[INFO]: Recording started (Lang: {self.current_lang})...")
        self.recording_active = True
        self.icon.icon = self.img_active
        
        self.typist.currently_typed = ""
        self.typist.last_locked_time = 0
        
        self.client = TranscriptionClient(
            "localhost", 9099,
            lang=self.current_lang, model="turbo",
            transcription_callback=self.typist.on_transcription,
            log_transcription=False,
            send_last_n_segments=2000
        )
        
        def run():
            try:
                self.client()
            except Exception as e:
                print(f"[ERROR] Client thread: {e}")
                self.recording_active = False
                self.icon.icon = self.img_idle

        self.client_thread = threading.Thread(target=run, daemon=True)
        self.client_thread.start()

    def stop_recording(self):
        if not self.recording_active: return
        print("[INFO]: Recording stopped.")
        self.recording_active = False
        self.icon.icon = self.img_idle
        if self.client and hasattr(self.client, 'client'):
            self.client.client.recording = False

    def run(self):
        # Register signals
        signal.signal(signal.SIGUSR1, self.toggle)
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)
        
        print(f"[INFO]: Always-on client is running. PID: {os.getpid()}, Lang: {self.current_lang}")
        
        # Start icon in a separate thread
        icon_thread = threading.Thread(target=self.icon.run, daemon=True)
        icon_thread.start()
        
        # Keep the main thread alive to handle signals
        while True:
            time.sleep(0.5)

    def cleanup(self, signum=None, frame=None):
        print("\n[INFO]: Cleaning up...")
        self.stop_recording()
        self.icon.stop()
        PID_FILE = "/tmp/whisper_dictation.pid"
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        sys.exit(0)

def main():
    manager = DictationManager()
    manager.run()

if __name__ == "__main__":
    main()
