import os
import asyncio
import logging
from typing import Optional, List, Dict, Any, Union
import socket
import time
import re

import discord
from discord.ext import commands
from dotenv import load_dotenv
from mcrcon import MCRcon

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ]
)
logger = logging.getLogger("MineBuildBot")

# Загружаем переменные окружения
load_dotenv()

# Константы
MODERATOR_ROLE_ID = 1277399739561672845
WHITELIST_ROLE_ID = 1150073275184074803
CANDIDATE_ROLE_ID = 1187064873847365752
LOG_CHANNEL_ID = 1277415977549566024
CANDIDATE_CHAT_ID = 1362437237513519279

class MineBuildBot(commands.Bot):
    """Основной класс бота для сервера MineBuild."""
    
    def __init__(self) -> None:
        """Инициализация бота с нужными настройками."""
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        
    async def setup_hook(self) -> None:
        """Хук настройки для инициализации необходимых компонентов."""
        self.add_view(ApplicationView())  # Добавляем персистентные кнопки
        
    async def on_ready(self) -> None:
        """Вызывается когда бот успешно подключился к Discord."""
        logger.info(f'Бот {self.user} запущен!')


class RejectModal(discord.ui.Modal, title="Отказ в заявке"):
    """Модальное окно для указания причины отказа в заявке."""
    
    reason = discord.ui.TextInput(
        label="Укажите причину отказа",
        style=discord.TextStyle.paragraph,
        placeholder="Опишите, почему вы отказываете в заявке...",
        required=True,
        max_length=1024
    )

    def __init__(self, discord_id: str, message_url: str, is_candidate: bool = False) -> None:
        super().__init__()
        self.discord_id = discord_id
        self.message_url = message_url
        self.is_candidate = is_candidate

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Обработка отправки формы отказа."""
        try:
            # Получаем пользователя
            member = await interaction.guild.fetch_member(int(self.discord_id))
            if member:
                # Если это кандидат, снимаем с него роль
                if self.is_candidate:
                    candidate_role = interaction.guild.get_role(CANDIDATE_ROLE_ID)
                    if candidate_role and candidate_role in member.roles:
                        await member.remove_roles(candidate_role)
                        logger.info(f"Снята роль кандидата с пользователя {self.discord_id}")
                
                # Отправляем сообщение пользователю
                try:
                    await member.send(
                        f"# ❌ Вашей заявке было отказано.\n"
                        f"> Причина: {self.reason.value}\n\n"
                        f"Вы подавали заявку на сервер **MineBuild**. По всей видимости, "
                        f"она не подходит под наши критерии. Если считаете, что это ошибка, "
                        f"то смело пишите в <#1070354020964769904>."
                    )
                except discord.Forbidden:
                    logger.warning(f"Не удалось отправить личное сообщение пользователю {self.discord_id}")

            # Отправляем сообщение в лог-канал
            log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(
                    f"# Куратор <@{interaction.user.id}> отказал [заявке]({self.message_url}) по причине:\n"
                    f"> {self.reason.value}"
                )

            # Обновляем оригинальное сообщение
            view = discord.ui.View(timeout=None)
            button = discord.ui.Button(
                style=discord.ButtonStyle.red,
                label="Отказано",
                emoji="❎",
                disabled=True,
                custom_id=f"rejected_{self.discord_id}"
            )
            view.add_item(button)
            
            # Обновляем текст сообщения и view
            await interaction.message.edit(
                content=f"-# Заявка игрока <@{self.discord_id}> отклонена!",
                view=view
            )
            await interaction.response.send_message("Отказ в заявке успешно обработан.", ephemeral=True)

        except Exception as e:
            logger.error(f"Ошибка при обработке отказа: {e}", exc_info=True)
            await interaction.response.send_message(f"Произошла ошибка: {str(e)}", ephemeral=True)


class RejectButton(discord.ui.Button):
    """Кнопка для отклонения заявки."""
    
    def __init__(self, discord_id: str, is_candidate: bool = False) -> None:
        super().__init__(
            style=discord.ButtonStyle.red,
            label="Отказать",
            custom_id=f"reject_{discord_id}_{is_candidate}",
            emoji="❎"
        )
        self.is_candidate = is_candidate
        
    async def callback(self, interaction: discord.Interaction) -> None:
        """Обработчик нажатия кнопки отказа."""
        # Проверяем права пользователя
        if not has_moderation_permissions(interaction.user):
            await interaction.response.send_message(
                "У вас нет прав для отказа заявок. Необходимо быть администратором или модератором.", 
                ephemeral=True
            )
            return

        # Получаем URL сообщения
        message_url = interaction.message.jump_url
        parts = self.custom_id.split('_')
        discord_id = parts[1]
        is_candidate = len(parts) > 2 and parts[2] == 'True'

        # Показываем модальное окно для ввода причины
        await interaction.response.send_modal(RejectModal(discord_id, message_url, is_candidate))


class ApproveButton(discord.ui.Button):
    """Кнопка для одобрения заявки."""
    
    def __init__(self, discord_id: str, is_candidate: bool = False) -> None:
        super().__init__(
            style=discord.ButtonStyle.green,
            label="Одобрить",
            custom_id=f"approve_{discord_id}_{is_candidate}",
            emoji="✅"
        )
        self.is_candidate = is_candidate
        
    async def callback(self, interaction: discord.Interaction) -> None:
        """Обработчик нажатия кнопки одобрения."""
        # Проверяем права пользователя
        if not has_moderation_permissions(interaction.user):
            await interaction.response.send_message(
                "У вас нет прав для одобрения заявок. Необходимо быть администратором или модератором.", 
                ephemeral=True
            )
            return

        # Получаем информацию
        parts = self.custom_id.split('_')
        discord_id = parts[1]
        is_candidate = len(parts) > 2 and parts[2] == 'True'
        
        whitelist_role = interaction.guild.get_role(WHITELIST_ROLE_ID)
        candidate_role = interaction.guild.get_role(CANDIDATE_ROLE_ID)
        
        if not whitelist_role:
            await interaction.response.send_message("Роль для вайтлиста не найдена.", ephemeral=True)
            return

        try:
            # Получаем объект участника
            member = await interaction.guild.fetch_member(int(discord_id))
            if not member:
                await interaction.response.send_message("Пользователь не найден.", ephemeral=True)
                return

            # Отвечаем на взаимодействие сразу, чтобы не было таймаута
            await interaction.response.defer(ephemeral=True)

            # Отправляем сообщение в лог-канал
            log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(
                    f"## Куратор <@{interaction.user.id}> одобрил [заявку]({interaction.message.jump_url})."
                )

            # Получаем никнейм из заявки
            minecraft_nickname = extract_minecraft_nickname(interaction.message.embeds)
            
            if minecraft_nickname:
                # Если это кандидат, снимаем с него роль кандидата
                if is_candidate and candidate_role and candidate_role in member.roles:
                    await member.remove_roles(candidate_role)
                    logger.info(f"Снята роль кандидата с пользователя {discord_id} при одобрении")
                
                await process_approval(interaction, member, minecraft_nickname)
            else:
                await interaction.followup.send(
                    "Не удалось найти никнейм в заявке. Проверьте правильность заполнения заявки.",
                    ephemeral=True
                )
                
            # Добавляем роль вайтлиста
            await member.add_roles(whitelist_role)
            
            # Обновляем сообщение
            await update_approval_message(interaction.message, discord_id)
            
            # Отправляем личное сообщение пользователю
            await send_welcome_message(member)
            
        except Exception as e:
            logger.error(f"Ошибка при одобрении заявки: {e}", exc_info=True)
            await interaction.followup.send(f"Произошла ошибка: {str(e)}", ephemeral=True)


class CandidateButton(discord.ui.Button):
    """Кнопка для перевода в кандидаты."""
    
    def __init__(self, discord_id: str) -> None:
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="В кандидаты",
            custom_id=f"candidate_{discord_id}",
            emoji="🔍"
        )
        
    async def callback(self, interaction: discord.Interaction) -> None:
        """Обработчик нажатия кнопки перевода в кандидаты."""
        # Проверяем права пользователя
        if not has_moderation_permissions(interaction.user):
            await interaction.response.send_message(
                "У вас нет прав для управления кандидатами. Необходимо быть администратором или модератором.", 
                ephemeral=True
            )
            return

        # Получаем информацию
        discord_id = self.custom_id.split('_')[1]
        candidate_role = interaction.guild.get_role(CANDIDATE_ROLE_ID)
        
        if not candidate_role:
            await interaction.response.send_message("Роль кандидата не найдена.", ephemeral=True)
            return

        try:
            # Получаем объект участника
            member = await interaction.guild.fetch_member(int(discord_id))
            if not member:
                await interaction.response.send_message("Пользователь не найден.", ephemeral=True)
                return

            # Отвечаем на взаимодействие сразу, чтобы не было таймаута
            await interaction.response.defer(ephemeral=True)

            # Получаем никнейм из заявки
            minecraft_nickname = extract_minecraft_nickname(interaction.message.embeds)
            
            if minecraft_nickname:
                # Пробуем изменить никнейм
                try:
                    await member.edit(nick=minecraft_nickname)
                except discord.Forbidden:
                    logger.warning(f"Не удалось изменить никнейм пользователю {member.id}")
                    await interaction.followup.send(
                        "Не удалось изменить никнейм пользователя. Пожалуйста, сделайте это вручную.",
                        ephemeral=True
                    )
            else:
                await interaction.followup.send(
                    "Не удалось найти никнейм в заявке. Проверьте правильность заполнения заявки.",
                    ephemeral=True
                )
                
            # Добавляем роль кандидата
            await member.add_roles(candidate_role)
            
            # Обновляем сообщение с заявкой
            await update_candidate_message(interaction.message, discord_id)
            
            # Отправляем сообщение в канал кандидатов
            candidate_channel = interaction.guild.get_channel(CANDIDATE_CHAT_ID)
            if candidate_channel:
                await candidate_channel.send(
                    f"# Привет, <@{discord_id}>!\n"
                    f"Твоя заявка была отправлена на рассмотрение куратором <@{interaction.user.id}>.\n"
                    f"Ты получил временную роль кандидата, которая предоставляет доступ к этому каналу.\n"
                    f"В ближайшее время с тобой свяжутся для обсуждения деталей."
                )
            
            # Отправляем сообщение в лог
            log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(
                    f"## Куратор <@{interaction.user.id}> перевел игрока <@{discord_id}> в кандидаты. "
                    f"[Ссылка на заявку]({interaction.message.jump_url})"
                )
            
            # Отправляем сообщение куратору
            await interaction.followup.send(
                f"Игрок <@{discord_id}> успешно переведен в кандидаты и получил соответствующую роль.",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Ошибка при переводе в кандидаты: {e}", exc_info=True)
            await interaction.followup.send(f"Произошла ошибка: {str(e)}", ephemeral=True)


class ApplicationView(discord.ui.View):
    """Представление для заявок с персистентными кнопками."""
    
    def __init__(self) -> None:
        super().__init__(timeout=None)  # Делаем кнопки персистентными


async def create_application_message(
    channel: discord.TextChannel, 
    discord_id: str, 
    embed: discord.Embed
) -> bool:
    """
    Создает сообщение с заявкой в указанном канале.
    
    Args:
        channel: Канал Discord для отправки заявки
        discord_id: ID пользователя Discord
        embed: Embed с данными заявки
        
    Returns:
        bool: True если сообщение успешно отправлено, иначе False
    """
    try:
        # Создаем новые embeds
        embeds = []
        
        # Первый embed - основная информация
        main_embed = discord.Embed(
            title="📝 Основная информация",
            color=0x00E5A1,
            timestamp=embed.timestamp
        )
        
        # Второй embed - подробная информация
        details_embed = discord.Embed(
            title="📋 Подробная информация",
            color=0x00E5A1,
            timestamp=embed.timestamp
        )

        # Распределяем поля по embeds
        for field in embed.fields:
            # Пропускаем Discord ID
            if field.name == 'Ваш Discord ID пользователя':
                continue
                
            # Основная информация
            if field.name in ['Ваш никнейм в Minecraft', 'Ваш возраст', 'Опыт игры в Minecraft']:
                main_embed.add_field(
                    name=field.name,
                    value=field.value,
                    inline=True
                )
            # Подробная информация
            else:
                details_embed.add_field(
                    name=field.name,
                    value=field.value,
                    inline=False
                )

        # Добавляем embeds только если в них есть поля
        if len(main_embed.fields) > 0:
            embeds.append(main_embed)
        if len(details_embed.fields) > 0:
            embeds.append(details_embed)
        
        # Создаем view с кнопками в правильном порядке: сначала Одобрить, затем Отказать, в конце В кандидаты
        view = discord.ui.View(timeout=None)
        view.add_item(ApproveButton(discord_id))     # Первая кнопка - Одобрить
        view.add_item(RejectButton(discord_id))      # Вторая кнопка - Отказать
        view.add_item(CandidateButton(discord_id))   # Третья кнопка - В кандидаты
        
        await channel.send(
            content=f"-# ||<@&{MODERATOR_ROLE_ID}>||\n## <@{discord_id}> отправил заявку на сервер!",
            embeds=embeds,
            view=view
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке заявки: {e}", exc_info=True)
        return False


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
        any(role.id == MODERATOR_ROLE_ID for role in user.roles)
    )


def extract_minecraft_nickname(embeds: List[discord.Embed]) -> Optional[str]:
    """
    Извлекает никнейм Minecraft из embed-сообщений.
    
    Args:
        embeds: Список встроенных сообщений
        
    Returns:
        str или None: Никнейм пользователя в Minecraft или None если не найден
    """
    for embed in embeds:
        for field in embed.fields:
            if field.name == 'Ваш никнейм в Minecraft':
                return field.value
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
            
            if "уже в вайтлисте" in clean_response.lower():
                await interaction.followup.send(
                    f"Игрок {minecraft_nickname} уже находится в белом списке.",
                    ephemeral=True
                )
            elif "добавлен" in clean_response.lower() or "успешно" in clean_response.lower():
                await interaction.followup.send(
                    f"Игрок {minecraft_nickname} успешно добавлен в белый список!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"Команда выполнена, но получен неожиданный ответ: {clean_response}",
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


async def update_approval_message(message: discord.Message, discord_id: str) -> None:
    """
    Обновляет сообщение заявки при одобрении.
    
    Args:
        message: Сообщение Discord с заявкой
        discord_id: ID пользователя Discord
    """
    view = discord.ui.View(timeout=None)
    button = discord.ui.Button(
        style=discord.ButtonStyle.green,
        label="Одобрено",
        emoji="✅",
        disabled=True,
        custom_id=f"approved_{discord_id}"
    )
    view.add_item(button)
    
    await message.edit(
        content=f"-# Заявка игрока <@{discord_id}> одобрена!",
        view=view
    )


async def update_candidate_message(message: discord.Message, discord_id: str) -> None:
    """
    Обновляет сообщение заявки при переводе в кандидаты.
    
    Args:
        message: Сообщение Discord с заявкой
        discord_id: ID пользователя Discord
    """
    # Создаем новую view с неактивной кнопкой "На рассмотрении" и активными кнопками одобрения/отказа
    view = discord.ui.View(timeout=None)
    
    # Кнопка "На рассмотрении" (неактивная) - теперь первая
    candidate_button = discord.ui.Button(
        style=discord.ButtonStyle.primary,
        label="На рассмотрении",
        emoji="🔍",
        disabled=True,
        custom_id=f"candidate_disabled_{discord_id}"
    )
    
    # Кнопки одобрения и отказа для кандидата
    approve_button = ApproveButton(discord_id, is_candidate=True)
    reject_button = RejectButton(discord_id, is_candidate=True)
    
    # Добавляем кнопки в view в нужном порядке
    view.add_item(candidate_button)  # Первая кнопка - На рассмотрении (неактивная)
    view.add_item(approve_button)    # Вторая кнопка - Одобрить
    view.add_item(reject_button)     # Третья кнопка - Отказать
    
    await message.edit(
        content=f"-# Заявка игрока <@{discord_id}> отправлена на рассмотрение!",
        view=view
    )


async def send_welcome_message(member: discord.Member) -> None:
    """
    Отправляет приветственное сообщение пользователю.
    
    Args:
        member: Объект пользователя Discord
    """
    try:
        welcome_message = (
            "**Твоя заявка нам понравилась и ты допущен на сервер!**\n\n"
            "> <:pointPurple:1293951536451551376> Здесь ты можешь написать __подробную__ биографию своего персонажа:\n"
            "> <:empty:1293950977275199619><:subEntriesPurple:1293951605372354703> Пиши о чём угодно, кроме совсем безумного, __мультивёрса__.\n"
            "> <:empty:1293950977275199619><:subEntriesPurple:1293951605372354703> Помни, что на сервере НЕТ цивилизации, соответственно если ты киборг, то, возможно, из будущего или прошлого. Или тебя соорудил безумный учёный, который давно погребён под землёй.\n"
            "> <:empty:1293950977275199619><:subEntriesPurple:1293951605372354703> Продумай свои механики, почитай пример и биографии других игроков. С ними ты будешь до конца сезона и так просто поменять не сможешь. У тебя не может быть миллион плюсов и 2-3 минуса, и наоборот, не усложняй слишком сильно себе игру.\n"
            "> <:pointPurple:1293951536451551376> После написания биографии дождись технического задания от Кофейка, проверь всё в одиночном мире и только после этого подтверждай, переделывать потом будет очень сложно.\n"
            'Писать сюда ➥ <#1280238897418338304> (с тегом "Заявка на Новую БИО")\n'
            "<:pointPurple:1293951536451551376> Ты также можешь и не писать биографию, если хочешь просто поиграть, но тогда не жалуйся, что нет уникальных механик.\n\n\n"
            "**Наш чатик:** <#1150073742840565810>\n"
            "**Наш форумник:** <#1280238897418338304>\n"
            "**Наши новости:** <#1153038125589868564>\n"
            "**Наши биографии:** <#1279139724820217894>\n"
            "-# Заготовленное сообщение, но искреннее. По всем вопросам смело пиши в этот чат!"
        )
        await member.send(welcome_message)
    except discord.Forbidden:
        logger.warning(f"Не удалось отправить личное сообщение пользователю {member.id}")


# Глобальный объект бота
bot = MineBuildBot()

if __name__ == '__main__':
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))