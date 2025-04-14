import os
import asyncio
from dotenv import load_dotenv
from hypercorn.config import Config
from hypercorn.asyncio import serve
from app import app
from bot import MineBuildBot

load_dotenv()

bot = MineBuildBot()

async def run_bot():
    await bot.start(os.getenv('DISCORD_BOT_TOKEN'))

async def run_quart():
    config = Config()
    config.bind = ["0.0.0.0:5000"]
    app.bot = bot  # Делаем бота доступным в Quart-приложении
    await serve(app, config)

async def main():
    await asyncio.gather(
        run_bot(),
        run_quart()
    )

if __name__ == '__main__':
    asyncio.run(main()) 