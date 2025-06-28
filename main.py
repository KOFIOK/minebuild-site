"""
Главный файл для одновременного запуска веб-сайта MineBuild и Discord бота.

Архитектура:
- Веб-сайт: Flask/Quart приложение (app.py)
- Discord бот: Модульная архитектура (bot/main.py)
- Запуск: Асинхронный с использованием asyncio.gather()

Новые возможности бота:
- 🔄 Персистентные кнопки (работают после рестарта)
- 📝 Модульная структура (UI, утилиты, команды)
- 🎯 Автоматическое восстановление View при запуске
- 🛡️ Улучшенная обработка ошибок

Использование:
  python main.py - запуск сайта и бота одновременно
  CTRL+C - корректное завершение обоих компонентов
"""

import os
import asyncio
import signal
import sys
import traceback
import logging
import platform
from dotenv import load_dotenv

# Загружаем переменные окружения ПЕРЕД импортом других модулей
load_dotenv()

from hypercorn.config import Config
from hypercorn.asyncio import serve
from app import app
from bot.main import MineBuildBot
from bot.config import setup_logging

# Настройка логирования для бота
bot_logger = setup_logging()

# Настройка кодировки вывода для Windows
if platform.system() == 'Windows':
    # Изменяем кодировку вывода консоли на UTF-8
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Настройка дополнительного логирования для main.py
main_logger = logging.getLogger("MineBuildMain")
main_logger.setLevel(logging.INFO)
main_logger.propagate = False  # Отключаем передачу логов вверх по иерархии
if not main_logger.handlers:
    # Создаем консольный обработчик с поддержкой UTF-8
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    main_logger.addHandler(console_handler)
    
    # Добавляем файловый обработчик с кодировкой UTF-8
    file_handler = logging.FileHandler("main.log", encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    main_logger.addHandler(file_handler)

# Создаем один экземпляр бота для всего приложения
bot = MineBuildBot()

# Добавляем информацию о новой архитектуре
main_logger.info("=== MineBuild: Запуск интегрированного приложения ===")
main_logger.info("📱 Веб-сайт: Flask/Quart приложение")
main_logger.info("🤖 Discord бот: Модульная архитектура с персистентными кнопками")
main_logger.info("🔄 Поддержка: Автоматическое восстановление UI после рестарта")
main_logger.info("=" * 55)

# Флаг для отслеживания состояния завершения
shutdown_event = asyncio.Event()
# Флаг для защиты от повторного завершения
is_shutting_down = False

# Определяем, на какой ОС запущен скрипт
IS_WINDOWS = platform.system() == 'Windows'
main_logger.info(f"Операционная система: {platform.system()}")

async def run_bot():
    """Запускает бота Discord."""
    try:
        main_logger.info("🤖 Запускаем Discord бота (модульная архитектура)...")
        # Используем правильный метод запуска для нового бота
        discord_token = os.getenv('DISCORD_BOT_TOKEN')
        if not discord_token:
            main_logger.error("❌ DISCORD_BOT_TOKEN не найден в переменных окружения!")
            return
        main_logger.info("🔑 Discord токен найден, подключаемся к API...")
        await bot.start(discord_token)
    except asyncio.CancelledError:
        main_logger.info("🔌 Отключаем Discord бота...")
    except Exception as e:
        main_logger.error(f"❌ Ошибка при запуске Discord бота: {e}", exc_info=True)
    finally:
        # Убедимся, что соединение закрыто при любом исходе
        if hasattr(bot, 'is_ready') and bot.is_ready():
            main_logger.info("🔐 Закрытие соединения с Discord API...")
            await bot.close()

async def run_quart():
    """Запускает веб-сервер Quart."""
    config = Config()
    config.bind = ["0.0.0.0:5000"]
    config.use_reloader = False  # Отключаем автоперезагрузку для улучшения обработки сигналов
    
    try:
        main_logger.info("📱 Запускаем веб-сервер на 0.0.0.0:5000...")
        # Используем тот же экземпляр бота
        app.bot = bot
        main_logger.info("🔗 Интеграция Discord бота с веб-приложением завершена")
        
        # Используем shutdown_event для возможности остановки сервера
        await serve(app, config, shutdown_trigger=shutdown_event.wait)
    except asyncio.CancelledError:
        main_logger.info("🛑 Остановка веб-сервера...")
    except Exception as e:
        main_logger.error(f"❌ Ошибка при запуске веб-сервера: {e}", exc_info=True)

def handle_exit_signal(signame=None):
    """Обработчик сигналов завершения."""
    global is_shutting_down
    
    # Защита от повторного запуска процедуры завершения
    if is_shutting_down:
        return
    
    is_shutting_down = True
    main_logger.info(f"Получен сигнал {'выхода' if signame is None else signame}, завершаем работу...")
    
    # Устанавливаем событие для завершения hypercorn
    shutdown_event.set()
    
    # Останавливаем цикл событий, что приведет к завершению всех задач
    try:
        loop = asyncio.get_event_loop()
        
        # Отменяем все задачи кроме текущей
        for task in asyncio.all_tasks(loop):
            if task is not asyncio.current_task():
                task.cancel()
    except RuntimeError:
        # В случае если цикл событий недоступен
        main_logger.warning("Не удалось получить доступ к циклу событий для отмены задач")

# Обработчик сигнала для Windows
def windows_signal_handler(signal_type):
    """Обработчик сигналов для Windows."""
    if signal_type == signal.SIGINT:
        handle_exit_signal("SIGINT (CTRL+C)")
        return True  # Сигнализируем о перехвате сигнала
    return False

async def main():
    """Основная функция для запуска всех компонентов."""
    try:
        # Регистрируем обработчики сигналов в зависимости от платформы
        if IS_WINDOWS:
            # На Windows используем встроенный обработчик только для KeyboardInterrupt
            main_logger.info("Запуск на Windows: используем альтернативную обработку сигналов")
        else:
            # На Unix-подобных системах используем add_signal_handler
            main_logger.info("Запуск на Unix-подобной системе: используем стандартную обработку сигналов")
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(
                    sig,
                    lambda signame=sig.name: handle_exit_signal(signame)
                )
        
        main_logger.info("Для остановки сервиса нажмите CTRL+C")
        
        # Запускаем оба компонента асинхронно
        await asyncio.gather(
            run_bot(),
            run_quart(),
            return_exceptions=True  # Позволяет обрабатывать исключения индивидуально
        )
    except asyncio.CancelledError:
        main_logger.info("Корректное завершение задач...")
    except Exception as e:
        main_logger.error(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        # Убедимся, что shutdown_event установлен
        shutdown_event.set()
        
        # Используем 2-секундный таймаут на завершение
        try:
            # Убедимся, что бот закрылся правильно
            if hasattr(bot, 'is_ready') and bot.is_ready():
                main_logger.info("Закрытие соединения с Discord...")
                await asyncio.wait_for(bot.close(), timeout=2.0)
        except asyncio.TimeoutError:
            main_logger.warning("Превышен таймаут закрытия бота Discord")
        except Exception as e:
            main_logger.error(f"Ошибка при закрытии бота: {e}", exc_info=True)
        
        main_logger.info("Приложение остановлено.")

if __name__ == '__main__':
    try:
        if IS_WINDOWS:
            # Для Windows - перехватываем KeyboardInterrupt в основном потоке
            try:
                asyncio.run(main())
            except KeyboardInterrupt:
                main_logger.info("Перехвачен CTRL+C")
                handle_exit_signal("CTRL+C")
        else:
            # Для Unix-подобных систем используем стандартный подход
            asyncio.run(main())
    except KeyboardInterrupt:
        main_logger.info("Принудительное завершение через KeyboardInterrupt")
    except Exception as e:
        main_logger.error(f"Необработанное исключение: {str(e)}", exc_info=True)
        traceback.print_exc()  # Выводим полный стек-трейс
    finally:
        main_logger.info("Программа завершена.")
        # Даем время на запись логов
        try:
            for handler in main_logger.handlers:
                handler.close()
        except:
            pass
        sys.exit(0)