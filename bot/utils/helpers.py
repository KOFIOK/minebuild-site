"""
Общие утилиты для Discord бота MineBuild
"""

import logging
import discord
from typing import List, Dict, Any, Optional

from ..config import QUESTION_MAPPING
from ..config_manager import get_moderator_role_id

logger = logging.getLogger("MineBuildBot.Utils")


def has_moderation_permissions(user: discord.Member) -> bool:
    """
    Проверяет есть ли у пользователя права на модерацию.
    
    Args:
        user: Пользователь Discord
        
    Returns:
        bool: True если у пользователя есть права, иначе False
    """
    return (
        user.guild_permissions.administrator or
        any(role.id == get_moderator_role_id() for role in user.roles)
    )


def extract_minecraft_nickname(embeds: List[discord.Embed]) -> Optional[str]:
    """
    Извлекает никнейм Minecraft из embed-сообщений.
    
    Args:
        embeds: Список встроенных сообщений
        
    Returns:
        str или None: Никнейм пользователя в Minecraft или None если не найден
    """
    # Возможные названия полей с никнеймом
    nickname_field_names = [
        'Игровой никнейм в Minecraft',      # Новое название с сайта
        'Ваш никнейм в Minecraft',          # Старое название
        'Ваш никнейм в Minecraft:',         # С двоеточием
        'Никнейм в Minecraft',              # Сокращенный вариант
        'Minecraft никнейм',                # Альтернативный вариант
        'Ник в Minecraft',                  # Краткая форма
        'Никнейм Minecraft',                # Без предлога
        'Minecraft Nickname',               # Английский вариант
        'MC никнейм',                       # Сокращение MC
        'Игровой ник',                      # Без упоминания Minecraft
        'В игре ник',                       # Разговорная форма
        'Имя в игре'                        # Описательная форма
    ]
    
    for embed in embeds:
        # Сначала ищем точное совпадение
        for field in embed.fields:
            if field.name in nickname_field_names:
                nickname = field.value.strip()
                if nickname:  # Проверяем, что никнейм не пустой
                    logger.info(f"Найден никнейм Minecraft: '{nickname}' в поле '{field.name}'")
                    return nickname
        
        # Если точного совпадения нет, пробуем частичное совпадение
        for field in embed.fields:
            field_name_lower = field.name.lower()
            if any(keyword in field_name_lower for keyword in ['minecraft', 'никнейм', 'ник']):
                nickname = field.value.strip()
                if nickname:  # Проверяем, что никнейм не пустой
                    logger.info(f"Найден никнейм Minecraft по частичному совпадению: '{nickname}' в поле '{field.name}'")
                    return nickname
    
    # Если не нашли, логируем все поля для отладки
    logger.warning("❌ Никнейм Minecraft не найден в заявке!")
    logger.warning("📋 Доступные поля в embed:")
    for i, embed in enumerate(embeds):
        logger.warning(f"  Embed {i + 1}:")
        if not embed.fields:
            logger.warning("    (нет полей)")
        else:
            for j, field in enumerate(embed.fields):
                logger.warning(f"    Поле {j + 1}: '{field.name}' = '{field.value}'")
    
    logger.warning("🔍 Искали поля с названиями:")
    for name in nickname_field_names:
        logger.warning(f"  - '{name}'")
    logger.warning("🔍 А также поля, содержащие ключевые слова: 'minecraft', 'никнейм', 'ник'")
    
    return None


async def process_approval(
    interaction: discord.Interaction, 
    member: discord.Member, 
    minecraft_nickname: str
) -> None:
    """
    Обрабатывает процесс одобрения заявки.
    
    Args:
        interaction: Взаимодействие Discord
        member: Объект участника
        minecraft_nickname: Никнейм участника в Minecraft
    """
    from ..utils.minecraft import add_to_whitelist
    
    # Пробуем изменить никнейм
    try:
        await member.edit(nick=minecraft_nickname)
    except discord.Forbidden:
        logger.warning(f"Не удалось изменить никнейм пользователю {member.id}")
        await interaction.followup.send(
            "Не удалось изменить никнейм пользователя. Пожалуйста, сделайте это вручную.",
            ephemeral=True
        )
    
    # Добавляем в белый список через RCON
    await add_to_whitelist(interaction, minecraft_nickname)


def create_embed_with_fields(title: str, fields_data: List[Dict[str, Any]], timestamp=None) -> discord.Embed:
    """
    Создает Embed с полями данных.
    
    Args:
        title: Заголовок embed
        fields_data: Список словарей с данными полей
        timestamp: Временная метка (опционально)
        
    Returns:
        discord.Embed: Готовый embed объект
    """
    embed = discord.Embed(
        title=title,
        color=0x00ff00,  # Зеленый цвет
        timestamp=timestamp
    )
    
    for field_data in fields_data:
        field_name = QUESTION_MAPPING.get(field_data.get('id', ''), field_data.get('question', 'Неизвестный вопрос'))
        field_value = field_data.get('answer', 'Нет ответа')
        
        embed.add_field(
            name=field_name,
            value=field_value,
            inline=False
        )
    
    return embed


async def update_approval_message(message: discord.Message, discord_id: str) -> None:
    """
    Обновляет сообщение заявки при одобрении.
    
    Args:
        message: Сообщение Discord с заявкой
        discord_id: ID пользователя Discord
    """
    # Создаем новую view с неактивными кнопками
    view = discord.ui.View(timeout=None)
    button = discord.ui.Button(
        style=discord.ButtonStyle.green,
        label="Одобрено",
        emoji="✅",
        disabled=True,
        custom_id=f"approved_{discord_id}"
    )
    view.add_item(button)
    
    # Обновляем оригинальное сообщение, убирая упоминание роли модератора
    await message.edit(
        content=f"## Заявка игрока <@{discord_id}>",
        view=view
    )


async def update_candidate_message(message: discord.Message, discord_id: str) -> None:
    """
    Обновляет сообщение заявки при переводе в кандидаты.
    
    Args:
        message: Сообщение Discord с заявкой
        discord_id: ID пользователя Discord
    """
    # Создаем новую view с кнопками для кандидата
    view = discord.ui.View(timeout=None)
    
    # Импортируем классы кнопок локально чтобы избежать циклических импортов
    from ..ui.buttons import ApproveButton, RejectButton
    
    # Кнопка "На рассмотрении" (неактивная)
    candidate_button = discord.ui.Button(
        style=discord.ButtonStyle.primary,
        label="На рассмотрении",
        emoji="🔍",
        disabled=True,
        custom_id=f"candidate_disabled_{discord_id}"
    )
    
    # Добавляем кнопки в view в нужном порядке
    view.add_item(candidate_button)
    view.add_item(ApproveButton(discord_id, is_candidate=True))
    view.add_item(RejectButton(discord_id, is_candidate=True))
    
    # Обновляем оригинальное сообщение
    await message.edit(
        content=f"## Заявка кандидата <@{discord_id}>",
        view=view
    )


async def send_welcome_message(member: discord.Member) -> None:
    """
    Отправляет приветственное сообщение новому участнику.
    
    Args:
        member: Новый участник сервера
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()

    try:
        welcome_message = (
            "**Твоя заявка нам понравилась и ты допущен на сервер!**\n\n"

            #"> <:pointPurple:1293951536451551376> Здесь ты можешь написать __подробную__ биографию своего персонажа:\n"
            #"> <:empty:1293950977275199619><:subEntriesPurple:1293951605372354703> Пиши о чём угодно, кроме совсем безумного, __мультивёрса__.\n"
            #"> <:empty:1293950977275199619><:subEntriesPurple:1293951605372354703> Помни, что на сервере НЕТ цивилизации, соответственно если ты киборг, то, возможно, из будущего или прошлого. Или тебя соорудил безумный учёный, который давно погребён под землёй.\n"
            #"> <:empty:1293950977275199619><:subEntriesPurple:1293951605372354703> Продумай свои механики, почитай пример и биографии других игроков. С ними ты будешь до конца сезона и так просто поменять не сможешь. У тебя не может быть миллион плюсов и 2-3 минуса, и наоборот, не усложняй слишком сильно себе игру.\n"
            #"> <:pointPurple:1293951536451551376> После написания биографии дождись технического задания от Кофейка, проверь всё в одиночном мире и только после этого подтверждай, переделывать потом будет очень сложно.\n"
            #'Писать сюда ➥ <#1280238897418338304> (с тегом "Заявка на Новую БИО")\n'
            #"<:pointPurple:1293951536451551376> Ты также можешь и не писать биографию, если хочешь просто поиграть, но тогда не жалуйся, что нет уникальных механик.\n\n\n"
            
            "<:pointPurple:1293951536451551376> Сейчас идёт **МЕЖСЕЗОНЬЕ**, а это значит, что практически ничего делать не надо!\n"
            f"> <:empty:1293950977275199619><:subEntriesPurple:1293951605372354703> Вы только что получили роль Майнбилдовца. Вернитесь на [сайт]({os.getenv('WEB_URL')}) и обновите страницу.\n"
            "> <:empty:1293950977275199619><:subEntriesPurple:1293951605372354703> В личном кабинете (нажмите на свой аватар в правом верхнем углу) должна появится кнопка *__Скачать сборку__*.\n"
            "> <:empty:1293950977275199619><:subEntriesPurple:1293951605372354703> Дождитесь скачивания. В лаунчере создайте новый экземпляр игры и перекиньте файлы из архива в корневую папку нового экземпляра. Попробуйте зайти в игру.\n"
            "<:pointPurple:1293951536451551376> Если вы столкнулись с проблемами, сообщите об этом в нашем чатике!\n\n\n"
            "**Наш чатик:** <#1150073742840565810>\n"
            "**Наш форумник:** <#1280238897418338304>\n"
            "**Наши новости:** <#1153038125589868564>\n"
            "**Наши биографии (неактуально):** <#1279139724820217894>\n"
            "-# Заготовленное сообщение, но искреннее. По всем вопросам смело пиши в чат общения!"
        )
        await member.send(welcome_message)
        logger.info(f"Приветственное сообщение отправлено пользователю {member.id}")
        
    except discord.Forbidden:
        logger.warning(f"Не удалось отправить приветственное сообщение пользователю {member.id} - ЛС закрыты")
    except Exception as e:
        logger.error(f"Ошибка при отправке приветственного сообщения: {e}", exc_info=True)
