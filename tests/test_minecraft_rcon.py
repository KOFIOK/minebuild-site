"""
Тесты для модуля minecraft с новой асинхронной RCON реализацией
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import os

from bot.utils.minecraft import _execute_rcon_command, execute_minecraft_command


class TestMinecraftRCON:
    """Тестируем новую асинхронную RCON реализацию."""
    
    def setup_method(self):
        """Настройка тестовых данных."""
        # Настраиваем тестовые переменные окружения
        os.environ['RCON_HOST'] = 'localhost'
        os.environ['RCON_PORT'] = '25575'
        os.environ['RCON_PASSWORD'] = 'test_password'
    
    @pytest.mark.asyncio
    async def test_execute_rcon_command_timeout_behavior(self):
        """Тестируем правильную обработку таймаутов в новой реализации."""
        # Проверяем, что функция корректно обрабатывает таймауты
        with patch('bot.utils.minecraft.asyncio.open_connection') as mock_connect:
            # Симулируем таймаут соединения
            mock_connect.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(asyncio.TimeoutError):
                await _execute_rcon_command("test command", timeout=1)
    
    @pytest.mark.asyncio
    async def test_execute_minecraft_command_server_unavailable(self):
        """Тестируем поведение когда сервер недоступен."""
        with patch('bot.utils.minecraft.check_minecraft_server_availability') as mock_check:
            mock_check.return_value = False
            
            result = await execute_minecraft_command("test command")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_execute_minecraft_command_success_simulation(self):
        """Симулируем успешное выполнение команды."""
        with patch('bot.utils.minecraft.check_minecraft_server_availability') as mock_check, \
             patch('bot.utils.minecraft._execute_rcon_command') as mock_rcon:
            
            mock_check.return_value = True
            mock_rcon.return_value = "Command executed successfully"
            
            result = await execute_minecraft_command("test command")
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_execute_minecraft_command_error_response(self):
        """Тестируем обработку ошибок в ответе сервера."""
        with patch('bot.utils.minecraft.check_minecraft_server_availability') as mock_check, \
             patch('bot.utils.minecraft._execute_rcon_command') as mock_rcon:
            
            mock_check.return_value = True
            mock_rcon.return_value = "Error: Unknown command"
            
            result = await execute_minecraft_command("invalid command")
            
            assert result is False
    
    def test_imports_no_mcrcon_dependency(self):
        """Проверяем, что mcrcon больше не импортируется."""
        import bot.utils.minecraft
        
        # Проверяем, что MCRcon не используется в модуле
        module_dict = vars(bot.utils.minecraft)
        assert 'MCRcon' not in module_dict
        
        # Проверяем, что threading и time не импортированы (так как больше не нужны)
        assert 'threading' not in module_dict
        assert 'time' not in module_dict
    
    def test_async_rcon_implementation_structure(self):
        """Проверяем, что новая функция _execute_rcon_command существует и является асинхронной."""
        from bot.utils.minecraft import _execute_rcon_command
        
        assert asyncio.iscoroutinefunction(_execute_rcon_command)
