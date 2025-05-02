import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch

# Добавляем корневую директорию проекта в путь Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot import MineBuildBot, MineBuildCommands

@pytest.fixture
async def bot():
    """Фикстура для создания экземпляра бота для тестов."""
    with patch('discord.ext.commands.Bot.start', new_callable=AsyncMock) as _:
        bot_instance = MineBuildBot()
        yield bot_instance

@pytest.mark.asyncio
async def test_bot_initialization(bot):
    """Тест инициализации бота."""
    assert bot is not None
    assert isinstance(bot, MineBuildBot)

@pytest.mark.asyncio
async def test_bot_on_ready(bot):
    """Тест события on_ready."""
    # Мок для тестирования on_ready
    with patch.object(bot, 'on_ready', new_callable=AsyncMock) as mock_on_ready:
        # Вызываем событие
        await bot.on_ready()
        # Проверяем, что метод был вызван
        mock_on_ready.assert_called_once()

@pytest.mark.asyncio
async def test_bot_setup_hook(bot):
    """Тест метода setup_hook."""
    # Патчим методы, которые вызываются внутри setup_hook
    with patch.object(bot, 'add_cog', new_callable=AsyncMock) as mock_add_cog, \
         patch.object(bot, 'add_view') as mock_add_view, \
         patch.object(bot.tree, 'sync', new_callable=AsyncMock) as mock_sync:
        
        # Вызываем метод setup_hook
        await bot.setup_hook()
        
        # Проверяем, что методы вызывались
        mock_add_cog.assert_called_once()
        mock_add_view.assert_called_once()
        mock_sync.assert_called_once()

@pytest.mark.asyncio
async def test_commands_cog():
    """Тест команд в коге MineBuildCommands."""
    # Создаем мок для бота
    mock_bot = AsyncMock(spec=MineBuildBot)
    
    # Создаем экземпляр кога с командами
    commands_cog = MineBuildCommands(mock_bot)
    
    # Проверяем наличие команд в коге
    assert hasattr(commands_cog, 'add_player')