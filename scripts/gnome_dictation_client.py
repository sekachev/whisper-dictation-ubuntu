import os
import sys
import time
import pyperclip
import evdev
from evdev import UInput, ecodes as e
from whisper_live.client import TranscriptionClient

# Настройка виртуального устройства ввода (клавиатуры)
# Это создает "железную" клавиатуру на уровне ядра
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

    def press_keys(self, keys):
        # Нажимаем все клавиши в списке
        for k in keys:
            self.ui.write(e.EV_KEY, k, 1)
        self.ui.syn()
        # Отпускаем их в обратном порядке
        for k in reversed(keys):
            self.ui.write(e.EV_KEY, k, 0)
        self.ui.syn()

    def backspace(self, count):
        if count <= 0:
            return
        # Для небольшого количества используем обычный бэкспейс
        if count < 10:
            for _ in range(count):
                self.press_keys([e.KEY_BACKSPACE])
                time.sleep(0.005)
        else:
            # Для большого количества (но не всего текста) тоже можно было бы оптимизировать, 
            # но пока оставим так или используем clear_all если это весь текст
            for _ in range(count):
                self.press_keys([e.KEY_BACKSPACE])
                time.sleep(0.002) # Ускоряем для больших пачек

    def clear_all(self):
        # Нажимаем Ctrl + A и затем Backspace
        self.press_keys([e.KEY_LEFTCTRL, e.KEY_A])
        time.sleep(0.02)
        self.press_keys([e.KEY_BACKSPACE])
        time.sleep(0.02)

    def paste_text(self, text):
        if not text:
            return
        # Копируем текст в буфер
        pyperclip.copy(text)
        time.sleep(0.05) # Пауза для Chrome
        
        # Нажимаем аппаратный Ctrl + V
        self.press_keys([e.KEY_LEFTCTRL, e.KEY_V])
        time.sleep(0.02)

    def on_transcription(self, full_text, segments):
        # Используем full_text, который сервер уже склеил с пробелами
        target_text = full_text
        
        if not target_text or target_text == self.currently_typed:
            return

        common_prefix_len = 0
        min_len = min(len(target_text), len(self.currently_typed))
        for i in range(min_len):
            if target_text[i] == self.currently_typed[i]:
                common_prefix_len += 1
            else:
                break
        
        chars_to_delete = len(self.currently_typed) - common_prefix_len
        text_to_add = target_text[common_prefix_len:]
        
        # Log for debugging
        print(f"[DEBUG]: Typed len: {len(self.currently_typed)}, Target len: {len(target_text)}, Common: {common_prefix_len}, To delete: {chars_to_delete}, To add: '{text_to_add}'")

        # Если изменений слишком много, стираем всё через Ctrl+A
        if chars_to_delete > 100:
            print(f"[DEBUG]: Threshold 100 exceeded! Clearing all ({len(self.currently_typed)} chars) and re-pasting")
            self.clear_all()
            self.currently_typed = ""
            self.paste_text(target_text)
            self.currently_typed = target_text
            return

        if chars_to_delete > 0:
            self.backspace(chars_to_delete)
        
        if text_to_add:
            self.paste_text(text_to_add)

        self.currently_typed = target_text

import signal

def main():
    # Save original clipboard content
    original_clipboard = None
    try:
        original_clipboard = pyperclip.paste()
        print("[INFO]: Original clipboard saved.")
    except Exception as e:
        print(f"[WARNING]: Could not save clipboard: {e}")

    typist = GNOMELiveTypist()
    
    def restore_clipboard(signum=None, frame=None):
        if original_clipboard is not None:
            print("\n[INFO]: Restoring original clipboard...")
            pyperclip.copy(original_clipboard)
        sys.exit(0)

    # Register signal handlers for graceful termination (e.g., from toggle_dictation.sh)
    signal.signal(signal.SIGTERM, restore_clipboard)
    signal.signal(signal.SIGINT, restore_clipboard)

    client = TranscriptionClient(
        "localhost", 9099,
        lang=None, model="turbo",
        transcription_callback=typist.on_transcription,
        log_transcription=False,
        send_last_n_segments=2000
    )
    
    print("[INFO]: Dictation started (evdev mode). Speak now!")
    try:
        client()
    except Exception as e:
        print(f"[ERROR]: {e}")
    finally:
        restore_clipboard()

if __name__ == "__main__":
    main()
