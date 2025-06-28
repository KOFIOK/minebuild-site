# MineBuild - Сайт и Discord-бот для Minecraft сервера

Комплексное решение для управления приватным Minecraft сервером: веб-сайт с системой заявок и донатов + Discord-бот с автоматическим управлением whitelist.

## 🎯 Возможности

### 🌐 Веб-сайт
- **Заявки** (`/apply`) - форма для вступления на сервер с Discord OAuth2
- **Донаты** (`/donate`) - интеграция с ЮMoney, автоматические привилегии
- **Информация** - правила, галерея построек, описание сервера

### 🤖 Discord-бот (модульная структура)
- **Обработка заявок** - интерактивные кнопки для модераторов
- **Автоматический whitelist** - добавление/удаление через RCON
- **Система донатов** - уведомления и выдача ролей
- **Мониторинг игроков** - отслеживание выхода с сервера

## 🚀 Быстрый старт

### Требования
- Python 3.8+
- Discord Bot Token
- Minecraft сервер с RCON

### Установка
```bash
git clone https://github.com/KOFIOK/minebuild-site.git
cd minebuild-site
pip install -r requirements.txt
```

### Настройка
Создайте `.env` файл:
```env
DISCORD_TOKEN=your_bot_token
GUILD_ID=your_server_id
RCON_HOST=your_minecraft_ip
RCON_PORT=25575
RCON_PASSWORD=your_rcon_password
YOOMONEY_SECRET_KEY=your_yoomoney_key
WEB_URL=http://127.0.0.1:5000
INTERNAL_API_KEY=your-secret-api-key
```

В `bot/config.py` настройте ID ролей и каналов:
```python
MODERATOR_ROLE_ID = your_moderator_role_id
WHITELIST_ROLE_ID = your_whitelist_role_id
LOG_CHANNEL_ID = your_log_channel_id
# и другие константы
```

### Запуск

#### Веб-сайт
```bash
python main.py
```
Сайт: `http://localhost:5000`

#### Discord-бот
```bash
# Вариант 1: Через новый скрипт
python run_bot.py

# Вариант 2: Прямо через модуль
python -m bot.main
```

## 🎮 Примеры использования

### Обработка заявки
```
Игрок подает заявку → Бот создает сообщение с кнопками → Модератор нажимает "Одобрить"
→ Роль выдана → Добавлен в whitelist → Отправлено приветствие
```

### Донат 500₽
```
Сайт → ЮMoney → Webhook → Бот:
"🎉 Новый донат! PlayerName - 500₽
✅ Роль "Благодетель" ✅ Суффикс [Донатер]"
```

### Команды бота
```bash
/add @user nickname  # Добавить игрока вручную
```

### Выход игрока
```
Игрок покинул Discord → Бот: "Исключить из whitelist? [Да] [Нет]"
```

## 🐛 Решение проблем

### Бот не работает
```bash
# Проверьте токен и права
tail -f bot.log
# Включите Intents в Discord Developer Portal
```

### RCON не подключается
```bash
# server.properties:
enable-rcon=true
rcon.port=25575
# Замените 'uw add' на 'whitelist add' в bot.py
```

### Заявки не приходят
```bash
# Проверьте ID канала в bot.py:
application_channel_id = ваш_ID_канала
# Права бота в канале: отправка сообщений, embed'ы
```

## 📋 Архитектура

### Веб-приложение
```
├── app.py              # Flask веб-приложение
├── auth.py             # Discord OAuth2 авторизация
├── main.py             # Точка входа для сайта
├── requirements.txt    # Зависимости
├── templates/          # HTML шаблоны
├── static/            # CSS, JS, изображения
└── tests/             # Тесты
```

### Discord-бот (модульная структура)
```
bot/
├── __init__.py         # Инициализация пакета
├── config.py           # Конфигурация и логирование  
├── main.py             # Основной класс бота
├── run_bot.py          # Скрипт запуска (в корне проекта)
├── cogs/               # Команды бота
│   └── admin.py        # Административные команды
├── ui/                 # UI компоненты Discord
│   ├── base.py         # Базовые классы
│   ├── buttons.py      # Кнопки для заявок
│   ├── modals.py       # Модальные окна
│   └── views.py        # Views для группировки UI
├── utils/              # Утилиты
│   ├── api.py          # Интеграция с веб API
│   ├── minecraft.py    # RCON интеграция
│   ├── helpers.py      # Общие функции
│   └── applications.py # Обработка заявок
└── logs/               # Логи бота
    ├── bot.log         # Основные логи
    └── discord.log     # Discord библиотека
```

## 🧪 Тестирование
```bash
pytest                    # Запуск тестов
pytest --cov=.           # С покрытием
```

## �️ Безопасность
- Проверка токенов донатов
- Валидация webhook ЮMoney
- Права доступа для модераторов
- Защита от спама заявок
- Логирование всех действий

## � Поддержка
1. Проверьте логи: `bot.log`, `main.log`
2. Убедитесь в правильности `.env`
3. Проверьте права бота в Discord
4. Создайте Issue с описанием проблемы

---
**MineBuild** - управление Minecraft сервером стало проще! 🎮
