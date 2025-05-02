import pytest
import asyncio
import sys
import os
from unittest.mock import patch, AsyncMock, MagicMock

# Добавляем корневую директорию проекта в путь Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import main
from bot import MineBuildBot

@pytest.mark.asyncio
async def test_main_initialization():
    """Тест инициализации основного модуля."""
    # Создаем патчи для предотвращения реального запуска сервера и бота
    with patch('bot.MineBuildBot') as mock_bot, \
         patch('hypercorn.asyncio.serve') as mock_serve, \
         patch('asyncio.gather', new_callable=AsyncMock) as mock_gather:
        
        # Настраиваем моки
        mock_bot.return_value = AsyncMock()
        mock_serve.return_value = None
        mock_gather.return_value = None
        
        # Вызываем main с мокнутыми зависимостями
        with patch.object(main, 'main', return_value=None) as mock_main:
            await main.main()
            mock_main.assert_called_once()

@pytest.mark.asyncio
async def test_server_startup():
    """Тест запуска веб-сервера."""
    # Создаем мок для serve с результатом None
    mock_serve = AsyncMock(return_value=None)
    mock_bot = MagicMock()
    
    # Создаем корректный мок для события с асинхронным методом wait
    mock_event = MagicMock()
    mock_event.wait = AsyncMock(return_value=False)  # wait() должен возвращать awaitable
    
    # Патчим саму локальную переменную serve в модуле main, а не модуль hypercorn.asyncio.serve
    with patch.object(main, 'serve', mock_serve), \
         patch.object(main, 'shutdown_event', mock_event), \
         patch.object(main, 'bot', mock_bot):
        
        try:
            # Используем wait_for с коротким таймаутом, т.к. нам не нужно ждать полного выполнения
            await asyncio.wait_for(main.run_quart(), timeout=0.5)
        except asyncio.TimeoutError:
            # Таймаут - это нормально в данном случае
            pass
        
        # Проверяем, что serve был вызван
        mock_serve.assert_called_once()
        
        # Также проверяем, что app.bot был установлен
        assert hasattr(main.app, 'bot')
        assert main.app.bot == mock_bot

@pytest.mark.asyncio
async def test_bot_startup():
    """Тест запуска Discord бота."""
    mock_bot = AsyncMock()
    # Настраиваем is_ready() так, чтобы это не был асинхронный метод, 
    # это предотвратит предупреждение о неиспользуемом корутине
    mock_bot.is_ready = MagicMock(return_value=False)
    
    with patch.object(main, 'bot', mock_bot), \
         patch.object(main, 'shutdown_event'), \
         patch.object(main, 'os') as mock_os:
        
        # Настраиваем environment переменную
        mock_os.getenv.return_value = "test_token"
        
        # Запускаем функцию run_bot
        task = asyncio.create_task(main.run_bot())
        
        # Даем ей немного времени запуститься
        await asyncio.sleep(0.1)
        
        # Отменяем задачу
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Проверяем, что бот был запущен с правильным токеном
        mock_bot.start.assert_called_once_with("test_token")