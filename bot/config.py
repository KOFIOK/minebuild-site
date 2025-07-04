"""
Конфигурация и настройка логирования для Discord бота MineBuild
"""

import os
import logging
import sys
import platform
from collections import defaultdict
from dotenv import load_dotenv

# Настройка кодировки вывода для Windows
if platform.system() == 'Windows':
    # Изменяем кодировку вывода консоли на UTF-8
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Загружаем переменные окружения
load_dotenv()


def setup_logging():
    """Настройка системы логирования для бота"""
    
    # Создаем директорию для логов если она не существует
    logs_dir = "bot/logs"
    try:
        os.makedirs(logs_dir, exist_ok=True)
        use_file_logging = True
    except (PermissionError, OSError):
        # Если не можем создать директорию (например, в CI/CD), используем только консоль
        use_file_logging = False
        print(f"⚠️ Не удалось создать директорию {logs_dir}, логи будут выводиться только в консоль")
    
    # Отключаем существующие обработчики корневого логгера
    for handler in logging.root.handlers:
        logging.root.removeHandler(handler)

    # Создаем список обработчиков
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # Добавляем файловый обработчик только если возможно
    if use_file_logging:
        try:
            handlers.append(logging.FileHandler("bot/logs/bot.log", encoding='utf-8'))
        except (PermissionError, OSError):
            print("⚠️ Не удалось создать файл лога, используется только консольный вывод")

    # Настройка основного логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # Создаем основной логгер бота
    logger = logging.getLogger("MineBuildBot")

    # Настраиваем логгер discord отдельно
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.INFO)
    if not discord_logger.handlers:
        discord_logger.addHandler(logging.StreamHandler(sys.stdout))
        # Добавляем файловый обработчик для Discord логов только если возможно
        if use_file_logging:
            try:
                discord_file_handler = logging.FileHandler("bot/logs/discord.log", encoding='utf-8')
                discord_file_handler.setFormatter(
                    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                )
                discord_logger.addHandler(discord_file_handler)
            except (PermissionError, OSError):
                pass  # Игнорируем ошибку, используем только консольный вывод
    
    return logger


# Константы Discord
MODERATOR_ROLE_ID = 1277399739561672845
WHITELIST_ROLE_ID = 1150073275184074803
CANDIDATE_ROLE_ID = 1187064873847365752
LOG_CHANNEL_ID = 1277415977549566024
CANDIDATE_CHAT_ID = 1362437237513519279

# Константы для донатов
DONATION_CHANNEL_ID = 1152974439311487089
DONATOR_ROLE_ID = 1153006749218000918

# Глобальный кэш для отслеживания заявок
recent_applications = defaultdict(list)
DEDUP_WINDOW = 60  # Окно в секундах для дедупликации

# Словарь соответствий ID вопросов их названиям
QUESTION_MAPPING = {
    'discord': 'Ваш Discord ID пользователя',
    'nickname': 'Ваш никнейм в Minecraft',
    'age': 'Ваш возраст',
    'experience': 'Опыт игры в Minecraft',
    'gameplay': 'Опишите ваш стиль игры',
    'important': 'Что для вас самое важное на приватных серверах?',
    'about': 'Расскажите о себе',
    'biography': 'Напишите краткую биографию'
}

# Переменные окружения
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0))
MINECRAFT_HOST = os.getenv('MINECRAFT_HOST', 'localhost')
MINECRAFT_PORT = int(os.getenv('MINECRAFT_PORT', 25575))
MINECRAFT_PASSWORD = os.getenv('MINECRAFT_PASSWORD', '')
WEB_API_URL = os.getenv('WEB_API_URL', 'http://localhost:5000')
API_SECRET_KEY = os.getenv('API_SECRET_KEY', '')
