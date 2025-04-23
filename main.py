import os
import asyncio
from dotenv import load_dotenv
from hypercorn.config import Config
from hypercorn.asyncio import serve
from app import app
from bot import MineBuildBot

load_dotenv()

# Создаем один экземпляр бота для всего приложения
bot = MineBuildBot()

async def run_bot():
    """Запускает бота Discord."""
    try:
        await bot.start(os.getenv('DISCORD_BOT_TOKEN'))
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")

async def run_quart():
    """Запускает веб-сервер Quart."""
    config = Config()
    config.bind = ["0.0.0.0:5000"]
    try:
        # Используем тот же экземпляр бота
        app.bot = bot
        await serve(app, config)
    except Exception as e:
        print(f"Ошибка при запуске веб-сервера: {e}")

async def main():
    """Основная функция для запуска всех компонентов."""
    try:
        # Запускаем оба компонента асинхронно
        await asyncio.gather(
            run_bot(),
            run_quart()
        )
    except Exception as e:
        print(f"Критическая ошибка: {e}")

if __name__ == '__main__':
    asyncio.run(main())