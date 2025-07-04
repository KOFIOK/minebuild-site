"""
Модуль для работы с Minecraft сервером через RCON
"""

import os
import asyncio
import logging
import socket
import re
from mcrcon import MCRcon
import discord

from ..config_manager import get_rcon_timeout, get_rcon_general_timeout, get_minecraft_commands

logger = logging.getLogger("MineBuildBot.Minecraft")


def _check_minecraft_server_availability_sync() -> bool:
    """
    Синхронная проверка доступности сервера Minecraft.
    
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


async def check_minecraft_server_availability() -> bool:
    """
    Проверяет доступность сервера Minecraft.
    
    Returns:
        bool: True если сервер доступен, иначе False
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _check_minecraft_server_availability_sync)


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
        
    # Пробуем подключиться к RCON в отдельном потоке
    try:
        import asyncio
        
        def sync_execute_command():
            """Синхронная версия выполнения команды для выполнения в executor"""
            try:
                with MCRcon(
                    os.getenv('RCON_HOST'),
                    os.getenv('RCON_PASSWORD'),
                    int(os.getenv('RCON_PORT')),
                    timeout=get_rcon_timeout()  # Таймаут для команды из конфигурации
                ) as mcr:
                    response = mcr.command(command)
                    
                    # Очищаем ответ от форматирования Minecraft
                    clean_response = re.sub(r'§[0-9a-fk-or]', '', response).strip()
                    
                    # Проверяем наличие ошибок
                    if "error" in clean_response.lower() or "ошибка" in clean_response.lower():
                        logger.error(f"Ошибка при выполнении команды {command}: {clean_response}")
                        return False
                        
                    return True
                    
            except Exception as e:
                logger.error(f"Ошибка в sync_execute_command: {e}", exc_info=True)
                return False
        
        # Выполняем синхронную функцию в executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, sync_execute_command)
        return result
            
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
        
    # Пробуем подключиться к RCON в отдельном потоке, чтобы не блокировать event loop
    try:
        def sync_add_to_whitelist():
            """Синхронная версия добавления в whitelist для выполнения в executor"""
            try:
                with MCRcon(
                    os.getenv('RCON_HOST'),
                    os.getenv('RCON_PASSWORD'),
                    int(os.getenv('RCON_PORT')),
                    timeout=10  # 10 секунд таймаут для команды
                ) as mcr:
                    # Получаем команду из конфигурации
                    commands = get_minecraft_commands()
                    command = commands["whitelist_add"].format(nickname=minecraft_nickname)
                    
                    response = mcr.command(command)
                    
                    # Очищаем ответ от форматирования Minecraft
                    clean_response = re.sub(r'§[0-9a-fk-or]', '', response).strip()
                    
                    return clean_response
                    
            except Exception as e:
                logger.error(f"Ошибка в sync_add_to_whitelist: {e}", exc_info=True)
                raise
        
        # Выполняем синхронную функцию в executor
        loop = asyncio.get_event_loop()
        clean_response = await loop.run_in_executor(None, sync_add_to_whitelist)
        
        # Проверяем различные возможные ответы от стандартной команды whitelist
        if any(phrase in clean_response.lower() for phrase in [
            "player is already whitelisted",
            "уже добавлен в белый список", 
            "already in the whitelist"
        ]):
            await interaction.followup.send(
                f"Игрок {minecraft_nickname} уже находится в белом списке.",
                ephemeral=True
            )
        elif any(phrase in clean_response.lower() for phrase in [
            "added to the whitelist",
            "добавлен в белый список",
            f"added {minecraft_nickname.lower()} to the whitelist"
        ]):
            logger.info(f"Игрок {minecraft_nickname} успешно добавлен в белый список")
        elif "player does not exist" in clean_response.lower() or "игрок не существует" in clean_response.lower():
            await interaction.followup.send(
                f"Игрок с никнеймом {minecraft_nickname} не найден. Проверьте правильность написания никнейма.",
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
        
    # Пробуем подключиться к RCON в отдельном потоке, чтобы не блокировать event loop
    try:
        def sync_add_to_whitelist():
            """Синхронная версия добавления в whitelist для выполнения в executor"""
            try:
                with MCRcon(
                    os.getenv('RCON_HOST'),
                    os.getenv('RCON_PASSWORD'),
                    int(os.getenv('RCON_PORT')),
                    timeout=10  # 10 секунд таймаут для команды
                ) as mcr:
                    # Получаем команду из конфигурации
                    commands = get_minecraft_commands()
                    command = commands["whitelist_add"].format(nickname=minecraft_nickname)
                    
                    response = mcr.command(command)
                    
                    # Очищаем ответ от форматирования Minecraft
                    clean_response = re.sub(r'§[0-9a-fk-or]', '', response).strip()
                    
                    return clean_response
                    
            except Exception as e:
                logger.error(f"Ошибка в sync_add_to_whitelist: {e}", exc_info=True)
                raise
        
        # Выполняем синхронную функцию в executor
        loop = asyncio.get_event_loop()
        clean_response = await loop.run_in_executor(None, sync_add_to_whitelist)
        
        # Проверяем различные возможные ответы от стандартной команды whitelist
        if any(phrase in clean_response.lower() for phrase in [
            "player is already whitelisted",
            "уже добавлен в белый список", 
            "already in the whitelist"
        ]):
            await response_channel.send(
                f"Игрок {minecraft_nickname} уже находится в белом списке.",
                ephemeral=hasattr(response_channel, 'followup')
            )
        elif any(phrase in clean_response.lower() for phrase in [
            "added to the whitelist",
            "добавлен в белый список",
            f"added {minecraft_nickname.lower()} to the whitelist"
        ]):
            logger.info(f"Игрок {minecraft_nickname} успешно добавлен в белый список")
        elif "player does not exist" in clean_response.lower() or "игрок не существует" in clean_response.lower():
            await response_channel.send(
                f"Игрок с никнеймом {minecraft_nickname} не найден. Проверьте правильность написания никнейма.",
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
        
    # Пробуем подключиться к RCON в отдельном потоке, чтобы не блокировать event loop
    try:
        def sync_remove_from_whitelist():
            """Синхронная версия удаления из whitelist для выполнения в executor"""
            try:
                with MCRcon(
                    os.getenv('RCON_HOST'),
                    os.getenv('RCON_PASSWORD'),
                    int(os.getenv('RCON_PORT')),
                    timeout=10  # 10 секунд таймаут для команды
                ) as mcr:
                    # Получаем команду из конфигурации
                    commands = get_minecraft_commands()
                    command = commands["whitelist_remove"].format(nickname=minecraft_nickname)
                    
                    response = mcr.command(command)
                    
                    # Очищаем ответ от форматирования Minecraft
                    clean_response = re.sub(r'§[0-9a-fk-or]', '', response).strip()
                    
                    return clean_response
                    
            except Exception as e:
                logger.error(f"Ошибка в sync_remove_from_whitelist: {e}", exc_info=True)
                raise
        
        # Выполняем синхронную функцию в executor
        loop = asyncio.get_event_loop()
        clean_response = await loop.run_in_executor(None, sync_remove_from_whitelist)
        
        # Проверяем успешность удаления с различными возможными ответами
        if any(phrase in clean_response.lower() for phrase in [
            "removed from the whitelist",
            "удален из белого списка",
            f"removed {minecraft_nickname.lower()} from the whitelist",
            f"{minecraft_nickname.lower()} removed from whitelist"
        ]):
            logger.info(f"Игрок {minecraft_nickname} успешно удален из белого списка")
            return True
        elif any(phrase in clean_response.lower() for phrase in [
            "player is not whitelisted",
            "не находится в белом списке",
            "not in the whitelist"
        ]):
            logger.warning(f"Игрок {minecraft_nickname} не был в белом списке")
            return True  # Считаем успешным, так как цель достигнута
        elif "player does not exist" in clean_response.lower() or "игрок не существует" in clean_response.lower():
            logger.error(f"Игрок {minecraft_nickname} не существует")
            return False
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


async def get_whitelist() -> list:
    """
    Получает список игроков в whitelist с сервера Minecraft через RCON.
    
    Returns:
        list: Список никнеймов игроков в whitelist, или пустой список при ошибке
    """
    # Проверяем доступность сервера
    is_server_available = await check_minecraft_server_availability()
    
    if not is_server_available:
        logger.error("Сервер Minecraft недоступен. Не удалось получить список whitelist")
        return []
        
    # Пробуем подключиться к RCON в отдельном потоке, чтобы не блокировать event loop
    try:
        import asyncio
        
        def sync_get_whitelist():
            """Синхронная версия получения whitelist для выполнения в executor"""
            try:
                # Используем контекстный менеджер с явным таймаутом
                with MCRcon(
                    os.getenv('RCON_HOST'),
                    os.getenv('RCON_PASSWORD'),
                    int(os.getenv('RCON_PORT')),
                    timeout=10  # 10 секунд таймаут для команды
                ) as mcr:
                    # Получаем команду из конфигурации
                    commands = get_minecraft_commands()
                    command = commands["whitelist_list"]
                    
                    response = mcr.command(command)
                    
                    # Очищаем ответ от форматирования Minecraft
                    clean_response = re.sub(r'§[0-9a-fk-or]', '', response).strip()
                    
                    # Парсим ответ
                    if "there are no whitelisted players" in clean_response.lower() or "нет игроков в белом списке" in clean_response.lower():
                        return []
                    elif "whitelisted players:" in clean_response.lower() or "игроки в белом списке:" in clean_response.lower():
                        # Извлекаем список игроков после двоеточия
                        players_part = clean_response.split(":", 1)
                        if len(players_part) > 1:
                            players_str = players_part[1].strip()
                            # Разделяем по запятым и очищаем от пробелов
                            players = [player.strip() for player in players_str.split(",") if player.strip()]
                            return players
                    
                    # Если формат ответа неожиданный, пытаемся извлечь никнеймы
                    # Ищем паттерны, похожие на никнеймы Minecraft
                    minecraft_nicknames = re.findall(r'\b[a-zA-Z0-9_]{3,16}\b', clean_response)
                    # Фильтруем общие слова
                    filtered_nicknames = [nick for nick in minecraft_nicknames if nick.lower() not in ['there', 'are', 'whitelisted', 'players', 'player']]
                    return filtered_nicknames
                    
            except Exception as e:
                logger.error(f"Ошибка в sync_get_whitelist: {e}", exc_info=True)
                return []
        
        # Выполняем синхронную функцию в executor с таймаутом
        loop = asyncio.get_event_loop()
        
        try:
            # Используем wait_for для добавления таймаута на выполнение в executor
            result = await asyncio.wait_for(
                loop.run_in_executor(None, sync_get_whitelist),
                timeout=15.0  # 15 секунд общий таймаут
            )
            return result
        except asyncio.TimeoutError:
            logger.error("Таймаут при получении whitelist - операция заняла более 15 секунд")
            return []
                
    except (socket.timeout, ConnectionRefusedError) as e:
        error_message = "Таймаут при подключении к серверу" if isinstance(e, socket.timeout) else "Соединение отклонено сервером"
        logger.error(f"{error_message}: {e}")
        return []
    except Exception as e:
        logger.error(f"Ошибка RCON при получении списка whitelist: {e}", exc_info=True)
        return []


