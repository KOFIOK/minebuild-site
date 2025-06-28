"""
Модуль для работы с заявками на сервер MineBuild
"""

import time
import logging
import discord
from typing import List, Dict, Any

from ..config import (
    recent_applications,
    DEDUP_WINDOW,
    MODERATOR_ROLE_ID
)

logger = logging.getLogger("MineBuildBot.Applications")


def create_embed_with_fields(title: str, fields_data: List[Dict[str, Any]], timestamp=None) -> discord.Embed:
    """
    Создает embed сообщение с заданными полями.
    
    Args:
        title: Заголовок embed сообщения
        fields_data: Список словарей с данными полей (name, value, inline)
        timestamp: Временная метка для embed
        
    Returns:
        discord.Embed: Созданное embed сообщение
    """
    embed = discord.Embed(
        title=title,
        color=0x00E5A1
    )
    if timestamp:
        embed.timestamp = timestamp

    for field in fields_data:
        embed.add_field(**field)
        
    return embed


async def create_application_message(
    channel: discord.TextChannel, 
    user_identifier: str, 
    embed: discord.Embed
) -> bool:
    """
    Создает сообщение с заявкой в указанном канале.
    
    Args:
        channel: Канал Discord для отправки заявки
        user_identifier: Идентификатор пользователя (может быть None для новой формы)
        embed: Embed с данными заявки
        
    Returns:
        bool: True если сообщение успешно отправлено, иначе False
    """
    try:
        # Если user_identifier не передан, это ошибка
        if user_identifier is None:
            logger.error("user_identifier не может быть None для создания заявки")
            return False
        
        # Проверяем на дубликаты (упрощенная проверка для веб-заявок)
        current_time = time.time()
        if user_identifier in recent_applications:
            recent_apps = recent_applications[user_identifier]
            
            # Очищаем старые записи
            recent_apps = [t for t in recent_apps if current_time - t < DEDUP_WINDOW]
            
            # Если есть недавние заявки, пропускаем
            if recent_apps:
                logger.warning(f"Обнаружен дубликат заявки для пользователя {user_identifier}. Пропускаем.")
                return False
                
            # Добавляем текущую заявку в список
            recent_apps.append(current_time)
            recent_applications[user_identifier] = recent_apps
        else:
            recent_applications[user_identifier] = [current_time]

        # Разделяем поля на основную и подробную информацию
        main_fields = []
        details_fields = []
        
        # Определяем поля для основной информации (должны соответствовать новым полям)
        inline_field_names = ['Игровой никнейм в Minecraft', 'Имя (реальное)', 'Возраст', 'Опыт игры в Minecraft']
        
        # Сохраняем все поля из embeds в отладочных целях
        all_field_names = [field.name for field in embed.fields]
        logger.info(f"Заявка от {user_identifier} содержит поля: {all_field_names}")
        
        for field in embed.fields:
            # Пропускаем поля с Discord ID
            if 'discord' in field.name.lower() or 'discord_id' == field.name:
                continue
                
            # Для каждого поля формируем словарь данных
            field_data = {
                'name': field.name,
                'value': field.value,
                'inline': field.name in inline_field_names
            }
            
            # Распределяем поля по категориям
            if field.name in inline_field_names:
                main_fields.append(field_data)
            else:
                details_fields.append(field_data)

        # Создаем embeds для канала
        embeds = []
        
        # Добавляем основную информацию (если есть)
        if main_fields:
            embeds.append(create_embed_with_fields(
                "📝 Основная информация",
                main_fields,
                embed.timestamp
            ))
        
        # Добавляем подробную информацию (если есть)
        if details_fields:
            logger.info(f"Добавляем подробную информацию: {details_fields}")
            embeds.append(create_embed_with_fields(
                "📋 Подробная информация",
                details_fields,
                embed.timestamp
            ))
        else:
            logger.warning(f"Отсутствуют поля для подробной информации в заявке пользователя {user_identifier}")

        # Проверяем, есть ли хоть один embed для отправки
        if not embeds:
            logger.error(f"Отсутствуют поля для отображения в заявке пользователя {user_identifier}")
            return False

        # Отправляем заявку в канал
        view = None
        
        # Проверяем, что у нас есть Discord ID для добавления кнопок
        if user_identifier and not user_identifier.startswith('web_user_'):
            # Импортируем View локально, чтобы избежать циклических импортов
            from ..ui.views import PersistentApplicationView
            
            # Обычная заявка через Discord
            view = PersistentApplicationView.create_for_application(user_identifier, is_candidate=False)
            content_prefix = f"-# <@&{MODERATOR_ROLE_ID}>\n"
            content = f"{content_prefix}## Заявка игрока <@{user_identifier}>"
        elif user_identifier and user_identifier.isdigit():
            # Импортируем View локально, чтобы избежать циклических импортов
            from ..ui.views import PersistentApplicationView
            
            # Заявка с сайта с валидным Discord ID
            view = PersistentApplicationView.create_for_application(user_identifier, is_candidate=False)
            content_prefix = f"-# <@&{MODERATOR_ROLE_ID}>\n"
            content = f"{content_prefix}## Заявка игрока <@{user_identifier}>"
        else:
            # Заявка без Discord ID или с неверным форматом
            content_prefix = f"-# <@&{MODERATOR_ROLE_ID}>\n"
            content = f"{content_prefix}## Получена заявка с сайта!"
            view = None  # Не добавляем кнопки если нет валидного Discord ID
        
        message = await channel.send(
            content=content,
            embeds=embeds,
            view=view
        )
        
        # Записываем в лог ID сообщения для отладки
        logger.info(f"Отправлена заявка с ID сообщения: {message.id}")

        # Отправляем копию заявки пользователю (если есть валидный Discord ID)
        if user_identifier and user_identifier.isdigit():
            try:
                user = await channel.guild.fetch_member(int(user_identifier))
                if user:
                    user_embeds = []
                    
                    # Копируем основную информацию для пользователя
                    if main_fields:
                        user_main_embed = create_embed_with_fields(
                            "📝 Ваша заявка (основная информация)",
                            main_fields,
                            embed.timestamp
                        )
                        user_main_embed.description = "Ваша заявка успешно отправлена на рассмотрение!"
                        user_embeds.append(user_main_embed)
                    
                    # Копируем подробную информацию для пользователя
                    if details_fields:
                        user_details_embed = create_embed_with_fields(
                            "📋 Ваша заявка (подробная информация)",
                            details_fields,
                            embed.timestamp
                        )
                        user_embeds.append(user_details_embed)

                    # Отправляем пользователю копию заявки
                    await user.send(
                        content="# ✅ Ваша заявка успешно отправлена!\nОжидайте решения кураторов набора. Вы получите уведомление, когда заявка будет рассмотрена.",
                        embeds=user_embeds
                    )
            except discord.Forbidden:
                logger.warning(f"Не удалось отправить личное сообщение пользователю {user_identifier}")
            except Exception as e:
                logger.error(f"Ошибка при отправке копии заявки пользователю: {e}", exc_info=True)

        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке заявки: {e}", exc_info=True)
        return False
