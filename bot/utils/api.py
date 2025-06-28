"""
Модуль для работы с веб API сайта MineBuild
"""

import os
import logging
import requests
from typing import Optional

logger = logging.getLogger("MineBuildBot.API")


async def update_web_application_status(discord_id: str, status: str, reason: str = '') -> bool:
    """
    Обновляет статус заявки на веб-сайте.
    
    Args:
        discord_id: ID пользователя Discord  
        status: Новый статус ('approved', 'rejected', 'candidate')
        reason: Причина (для отказов)
        
    Returns:
        bool: True если статус успешно обновлен, иначе False
    """
    try:
        # URL веб-сайта (должен быть настроен в переменных окружения)
        web_url = os.getenv('WEB_URL', 'http://127.0.0.1:5000')
        api_key = os.getenv('INTERNAL_API_KEY', 'your-secret-api-key')
        
        # Данные для отправки
        data = {
            'discord_id': discord_id,
            'status': status,
            'reason': reason
        }
        
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        }
        
        # Отправляем POST запрос к API
        response = requests.post(
            f"{web_url}/api/update-application-status",
            json=data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Статус заявки успешно обновлен на сайте для пользователя {discord_id}: {status}")
            return True
        else:
            logger.error(f"Ошибка при обновлении статуса на сайте: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при отправке обновления статуса на сайт: {e}")
        return False


async def clear_web_application_status(discord_id: str) -> bool:
    """
    Очищает статус заявки на веб-сайте, позволяя пользователю подать новую заявку.
    
    Args:
        discord_id: ID пользователя Discord  
        
    Returns:
        bool: True если статус успешно очищен, иначе False
    """
    try:
        # URL веб-сайта (должен быть настроен в переменных окружения)
        web_url = os.getenv('WEB_URL', 'http://127.0.0.1:5000')
        api_key = os.getenv('INTERNAL_API_KEY', 'your-secret-api-key')
        
        # Данные для отправки
        data = {
            'discord_id': discord_id
        }
        
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        }
        
        # Отправляем POST запрос к API
        response = requests.post(
            f"{web_url}/api/clear-application-status",
            json=data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Статус заявки успешно очищен на сайте для пользователя {discord_id}")
            return True
        else:
            logger.error(f"Ошибка при очистке статуса на сайте: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при отправке запроса очистки статуса на сайт: {e}")
        return False
