"""
Модуль для работы с Minecraft сервером через RCON
"""

import os
import asyncio
import logging
import socket
import re
from typing import Optional, Union
from mcrcon import MCRcon
import discord

logger = logging.getLogger("MineBuildBot.Minecraft")


async def check_minecraft_server_availability() -> bool:
    """
    Проверяет доступность сервера Minecraft.
    
    Returns:
        bool: True если сервер доступен, иначе False
    """
    try:
        host = os.getenv('RCON_HOST')
        port = int(os.getenv('RCON_PORT'))
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 секунд таймаут
        result = sock.connect_ex((host, port))
        sock.close()
        
        return result == 0
    except Exception as e:
        logger.error(f"Ошибка при проверке доступности сервера: {e}", exc_info=True)
        return False


async def execute_minecraft_command(command: str) -> bool:
    """
    Выполняет команду на сервере Minecraft через RCON.
    
    Args:
        command: Команда для выполнения
        
    Returns:
        bool: True если команда успешно выполнена, иначе False
    """
    # Проверяем доступность сервера
    is_server_available = await check_minecraft_server_availability()
    
    if not is_server_available:
        logger.error(f"Сервер Minecraft недоступен. Не удалось выполнить команду {command}")
        return False
        
    # Пробуем подключиться к RCON
    try:
        with MCRcon(
            os.getenv('RCON_HOST'),
            os.getenv('RCON_PASSWORD'),
            int(os.getenv('RCON_PORT'))
        ) as mcr:
            # Даем серверу время на обработку команды
            await asyncio.sleep(1)
            response = mcr.command(command)
            
            # Очищаем ответ от форматирования Minecraft
            clean_response = re.sub(r'§[0-9a-fk-or]', '', response).strip()
            logger.info(f"RCON response: {clean_response}")
            
            # Проверяем наличие ошибок
            if "error" in clean_response.lower() or "ошибка" in clean_response.lower():
                logger.error(f"Ошибка при выполнении команды {command}: {clean_response}")
                return False
                
            return True
            
    except (socket.timeout, ConnectionRefusedError) as e:
        error_message = "Таймаут при подключении к серверу" if isinstance(e, socket.timeout) else "Соединение отклонено сервером"
        logger.error(f"{error_message}: {e}")
        return False
    except Exception as e:
        logger.error(f"Ошибка RCON: {e}", exc_info=True)
        return False


async def add_to_whitelist(interaction: discord.Interaction, minecraft_nickname: str) -> None:
    """
    Добавляет игрока в белый список сервера.
    
    Args:
        interaction: Взаимодействие Discord
        minecraft_nickname: Никнейм игрока в Minecraft
    """
    # Проверяем доступность сервера
    is_server_available = await check_minecraft_server_availability()
    
    if not is_server_available:
        await interaction.followup.send(
            "Сервер Minecraft недоступен. Пожалуйста, проверьте его состояние и добавьте игрока в белый список вручную.",
            ephemeral=True
        )
        return
        
    # Пробуем подключиться к RCON
    try:
        with MCRcon(
            os.getenv('RCON_HOST'),
            os.getenv('RCON_PASSWORD'),
            int(os.getenv('RCON_PORT'))
        ) as mcr:
            # Даем серверу время на обработку команды
            await asyncio.sleep(1)
            response = mcr.command(f"uw add {minecraft_nickname}")
            
            # Очищаем ответ от форматирования Minecraft
            clean_response = re.sub(r'§[0-9a-fk-or]', '', response).strip()
            logger.info(f"RCON response: {clean_response}")
            
            # Отправляем сообщение только если есть ошибка
            if "уже в вайтлисте" in clean_response.lower():
                await interaction.followup.send(
                    f"Игрок {minecraft_nickname} уже находится в белом списке.",
                    ephemeral=True
                )
    except (socket.timeout, ConnectionRefusedError) as e:
        error_message = "Таймаут при подключении к серверу" if isinstance(e, socket.timeout) else "Соединение отклонено сервером"
        logger.error(f"{error_message}: {e}")
        await interaction.followup.send(
            f"{error_message}. Пожалуйста, добавьте игрока вручную.",
            ephemeral=True
        )
    except Exception as e:
        logger.error(f"Ошибка RCON: {e}", exc_info=True)
        await interaction.followup.send(
            f"Произошла ошибка при добавлении в белый список: {str(e)}. Пожалуйста, добавьте игрока вручную.",
            ephemeral=True
        )


async def add_to_whitelist_wrapper(response_channel, minecraft_nickname: str) -> None:
    """
    Обертка для функции add_to_whitelist, которая работает с разными типами контекста.
    
    Args:
        response_channel: Объект для отправки ответов (может быть Context или Follow-up)
        minecraft_nickname: Никнейм игрока в Minecraft
    """
    # Проверяем доступность сервера
    is_server_available = await check_minecraft_server_availability()
    
    if not is_server_available:
        await response_channel.send(
            "Сервер Minecraft недоступен. Пожалуйста, проверьте его состояние и добавьте игрока в белый список вручную.",
            ephemeral=hasattr(response_channel, 'followup')
        )
        return
        
    # Пробуем подключиться к RCON
    try:
        with MCRcon(
            os.getenv('RCON_HOST'),
            os.getenv('RCON_PASSWORD'),
            int(os.getenv('RCON_PORT'))
        ) as mcr:
            # Даем серверу время на обработку команды
            await asyncio.sleep(1)
            response = mcr.command(f"uw add {minecraft_nickname}")
            
            # Очищаем ответ от форматирования Minecraft
            clean_response = re.sub(r'§[0-9a-fk-or]', '', response).strip()
            logger.info(f"RCON response: {clean_response}")
            
            # Отправляем сообщение только если есть ошибка
            if "уже в вайтлисте" in clean_response.lower():
                await response_channel.send(
                    f"Игрок {minecraft_nickname} уже находится в белом списке.",
                    ephemeral=hasattr(response_channel, 'followup')
                )
    except (socket.timeout, ConnectionRefusedError) as e:
        error_message = "Таймаут при подключении к серверу" if isinstance(e, socket.timeout) else "Соединение отклонено сервером"
        logger.error(f"{error_message}: {e}")
        await response_channel.send(
            f"{error_message}. Пожалуйста, добавьте игрока вручную.",
            ephemeral=hasattr(response_channel, 'followup')
        )
    except Exception as e:
        logger.error(f"Ошибка RCON: {e}", exc_info=True)
        await response_channel.send(
            f"Произошла ошибка при добавлении в белый список: {str(e)}. Пожалуйста, добавьте игрока вручную.",
            ephemeral=hasattr(response_channel, 'followup')
        )


async def remove_from_whitelist(minecraft_nickname: str) -> bool:
    """
    Удаляет игрока из белого списка сервера.
    
    Args:
        minecraft_nickname: Никнейм игрока в Minecraft
        
    Returns:
        bool: True если игрок успешно удален, иначе False
    """
    # Проверяем доступность сервера
    is_server_available = await check_minecraft_server_availability()
    
    if not is_server_available:
        logger.error(f"Сервер Minecraft недоступен. Не удалось удалить игрока {minecraft_nickname} из белого списка")
        return False
        
    # Пробуем подключиться к RCON
    try:
        with MCRcon(
            os.getenv('RCON_HOST'),
            os.getenv('RCON_PASSWORD'),
            int(os.getenv('RCON_PORT'))
        ) as mcr:
            # Даем серверу время на обработку команды
            await asyncio.sleep(1)
            response = mcr.command(f"uw remove {minecraft_nickname}")
            
            # Очищаем ответ от форматирования Minecraft
            clean_response = re.sub(r'§[0-9a-fk-or]', '', response).strip()
            logger.info(f"RCON response: {clean_response}")
            
            # Проверяем успешность удаления
            if "удален" in clean_response.lower() or "removed" in clean_response.lower():
                logger.info(f"Игрок {minecraft_nickname} успешно удален из белого списка")
                return True
            else:
                logger.error(f"Не удалось удалить игрока {minecraft_nickname} из белого списка: {clean_response}")
                return False
                
    except (socket.timeout, ConnectionRefusedError) as e:
        error_message = "Таймаут при подключении к серверу" if isinstance(e, socket.timeout) else "Соединение отклонено сервером"
        logger.error(f"{error_message}: {e}")
        return False
    except Exception as e:
        logger.error(f"Ошибка RCON при удалении из белого списка: {e}", exc_info=True)
        return False
