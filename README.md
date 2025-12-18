# Whisper Dictation for Ubuntu (GNOME/Wayland)

Этот проект превращает [WhisperLive](https://github.com/CollaboraOnline/WhisperLive) в полноценный системный сервис для Ubuntu с поддержкой глобальной диктовки по горячей клавише. 

## Особенности
- **Глобальная диктовка**: Работает в любом приложении (Chrome, Telegram, IDE).
- **Живой вывод**: Текст печатается сразу, как только вы говорите.
- **Предзагрузка модели**: Сервер держит модель в памяти для мгновенного старта.
- **Интеграция с GNOME**: Удобное переключение одной кнопкой.

## Установка

```bash
git clone https://github.com/sekachev/whisper-dictation-ubuntu.git
cd whisper-dictation-ubuntu
chmod +x install.sh
./install.sh
```

## Настройка горячей клавиши

1. Откройте **Settings** -> **Keyboard** -> **View and Customize Shortcuts**.
2. В самом низу выберите **Custom Shortcuts**.
3. Нажмите **+** и введите:
   - **Name**: Whisper Dictation
   - **Command**: `/bin/bash /путь/к/проекту/WhisperLive/toggle_dictation.sh`
   - **Shortcut**: Любая удобная клавиша (например, `Super + D`).

## Управление сервисом

Сервер транскрипции работает как системный сервис:

- Проверить статус: `sudo systemctl status whisper-server`
- Посмотреть логи (живое логгирование): `journalctl -u whisper-server -f`
- Перезагрузить: `sudo systemctl restart whisper-server`

## Технические детали
- Используется библиотека `evdev` для имитации нажатий клавиш (минуя ограничения Wayland).
- Для работы в Chrome используется автоматическая вставка через буфер обмена (`Ctrl+V`).
- По умолчанию используется модель `turbo`.

---
*Основано на репозитории [WhisperLive](https://github.com/CollaboraOnline/WhisperLive).*
