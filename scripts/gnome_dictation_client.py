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
        self.last_locked_time = 0

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
            # Для большого количества тоже используем бэкспейс, но чуть быстрее
            for _ in range(count):
                self.press_keys([e.KEY_BACKSPACE])
                time.sleep(0.002)

    def clear_all(self):
        # Эта функция больше не используется для предотвращения полной очистки поля
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
        # Список галлюцинаций
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
            "субтитры подготовил"
        ]
        
        # 1. Фильтруем сегменты от галлюцинаций
        valid_segments = []
        for seg in segments:
            t = seg["text"].strip()
            if t.lower() in hallucinations:
                print(f"[DEBUG]: Hallucination ignored: '{t}'")
                continue
            valid_segments.append(seg)
            
        if not valid_segments:
            return

        # 2. Определяем границу "заморозки" (stability window)
        # Все, что старше 3 секунд от самого нового сегмента, помечаем как Locked
        current_max_time = float(valid_segments[-1].get("end", 0))
        
        lock_until_idx = 0
        for i, seg in enumerate(valid_segments):
            end_t = float(seg.get("end", 0))
            # Условие заморозки: сегмент завершен И он старше (max_time - 3.0)
            # ИЛИ это очень старый сегмент (на всякий случай, если окно сервера ушло далеко)
            if end_t <= self.last_locked_time:
                lock_until_idx = i + 1
                continue
                
            if seg.get("completed", False) and end_t < (current_max_time - 3.0):
                lock_until_idx = i + 1
                
                # Обновляем наш внутренний буфер: "забываем" про этот текст
                text_to_lock = seg["text"].strip()
                
                # Мы ищем этот текст в начале нашего буфера и отрезаем его
                if self.currently_typed.startswith(text_to_lock):
                    # Отрезаем текст и возможный пробел за ним
                    self.currently_typed = self.currently_typed[len(text_to_lock):].lstrip()
                    self.last_locked_time = end_t
                    print(f"[DEBUG]: Locking segment: '{text_to_lock}'. New baseline len: {len(self.currently_typed)}")
                else:
                    # Если текст почему-то не совпал (редко), просто сбрасываем буфер
                    # Это предотвратит попытку удаления "замороженного" текста
                    self.currently_typed = ""
                    self.last_locked_time = end_t
                    print(f"[DEBUG]: Desync in locking '{text_to_lock}', resetting baseline.")
            else:
                # Как только нашли первый незавершенный или "молодой" сегмент - стоп
                break
        
        # 3. Формируем целевой текст только из "активных" сегментов
        active_parts = [s["text"].strip() for s in valid_segments[lock_until_idx:]]
        target_text = " ".join(active_parts)
        
        if not target_text and not self.currently_typed:
            return
            
        if target_text == self.currently_typed:
            return

        # 4. Стандартная дифференциальная печать (только для активной зоны)
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
            print(f"[DEBUG]: Diff - Delete: {chars_to_delete}, Add: '{text_to_add}'")

        if chars_to_delete > 0:
            # Ограничиваем удаление, чтобы случайно не "вылететь" за границу заморозки
            if chars_to_delete > 200: 
                 print(f"[WARNING]: Unusual deletion size ({chars_to_delete}). Limiting.")
                 chars_to_delete = 200
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
