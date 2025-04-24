import os
import asyncio
import logging
from typing import Optional, List, Dict, Any, Union
import socket
import time
import re
from collections import defaultdict

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

# Глобальный кэш для отслеживания заявок
recent_applications = defaultdict(list)
DEDUP_WINDOW = 60  # Окно в секундах для дедупликации

class MineBuildBot(commands.Bot):
    """Основной класс бота для сервера MineBuild."""
    
    def __init__(self) -> None:
        """Инициализация бота с нужными настройками."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # Включены интенты на отслеживание пользователей
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None  # Отключаем стандартную команду help
        )
        
    async def setup_hook(self) -> None:
        """Хук настройки для инициализации необходимых компонентов."""
        # Регистрируем команды
        await self.add_cog(MineBuildCommands(self))
        # Добавляем представление с кнопками
        self.add_view(ApplicationView())
        # Синхронизируем команды для конкретного сервера
        try:
            guild_id = int(os.getenv('DISCORD_GUILD_ID', '0'))
            if guild_id:
                guild = discord.Object(id=guild_id)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"Команды синхронизированы для сервера {guild_id}")
            else:
                logger.warning("DISCORD_GUILD_ID не настроен, команды будут синхронизированы глобально")
                await self.tree.sync()
        except Exception as e:
            logger.error(f"Ошибка при синхронизации команд: {e}")
            await self.tree.sync()  # Fallback к глобальной синхронизации
        
    async def on_ready(self) -> None:
        """Вызывается когда бот успешно подключился к Discord."""
        logger.info(f"Бот {self.user} запущен и готов к работе!")

    async def on_member_remove(self, member: discord.Member) -> None:
        """Вызывается когда пользователь покидает сервер."""
        try:
            # Проверяем, есть ли у пользователя роль вайтлиста
            whitelist_role_id = WHITELIST_ROLE_ID
            has_whitelist = any(role.id == whitelist_role_id for role in member.roles)
            
            if has_whitelist:
                # Получаем никнейм пользователя
                nickname = member.nick or member.name
                
                # Отправляем уведомление в лог-канал
                log_channel = self.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    await send_member_leave_notification(log_channel, member.id, nickname)
                    logger.info(f"Отправлено уведомление о выходе пользователя {member.id} с ролью вайтлиста")
                else:
                    logger.error(f"Не удалось найти канал логов {LOG_CHANNEL_ID}")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке выхода пользователя: {e}", exc_info=True)


class MineBuildCommands(commands.Cog):
    """Класс с командами бота."""
    
    def __init__(self, bot: MineBuildBot):
        self.bot = bot

    @commands.hybrid_command(
        name="add",
        description="Добавить игрока на сервер (выдать роль, добавить в вайтлист)"
    )
    @commands.guild_only()
    @commands.has_any_role(MODERATOR_ROLE_ID)
    @discord.app_commands.describe(
        user="Пользователь Discord, которого нужно добавить",
        minecraft_nickname="Никнейм игрока в Minecraft"
    )
    async def add_player(
        self,
        ctx: Union[commands.Context, discord.Interaction],
        user: discord.Member,
        minecraft_nickname: str
    ):
        """
        Добавляет игрока на сервер: выдаёт роль, добавляет в вайтлист и отправляет приветственное сообщение.
        Работает как с /add, так и с !add
        """
        try:
            # Проверяем права пользователя
            if not has_moderation_permissions(ctx.author):
                await ctx.response.send_message(
                    "У вас нет прав для добавления игроков. Необходимо быть администратором или модератором.",
                    ephemeral=True
                ) if isinstance(ctx, discord.Interaction) else await ctx.reply(
                    "У вас нет прав для добавления игроков. Необходимо быть администратором или модератором."
                )
                return

            # Проверяем наличие роли вайтлиста
            whitelist_role = ctx.guild.get_role(WHITELIST_ROLE_ID)
            if not whitelist_role:
                await ctx.response.send_message(
                    "Роль для вайтлиста не найдена.", 
                    ephemeral=True
                ) if isinstance(ctx, discord.Interaction) else await ctx.reply(
                    "Роль для вайтлиста не найдена."
                )
                return

            # Отвечаем на взаимодействие в зависимости от типа контекста
            if isinstance(ctx, discord.Interaction):
                await ctx.response.defer(ephemeral=True)
                response_channel = ctx.followup
            else:
                response_channel = ctx

            # Если у пользователя есть роль кандидата, снимаем её
            candidate_role = ctx.guild.get_role(CANDIDATE_ROLE_ID)
            if candidate_role and candidate_role in user.roles:
                await user.remove_roles(candidate_role)
                logger.info(f"Снята роль кандидата с пользователя {user.id}")

            # Добавляем роль вайтлиста
            await user.add_roles(whitelist_role)
            
            try:
                # Пробуем изменить никнейм
                await user.edit(nick=minecraft_nickname)
            except discord.Forbidden:
                logger.warning(f"Не удалось изменить никнейм пользователю {user.id}")
                await response_channel.send(
                    "Не удалось изменить никнейм пользователя. Пожалуйста, сделайте это вручную.",
                    ephemeral=True
                )
            
            # Добавляем в вайтлист
            await add_to_whitelist_wrapper(response_channel, minecraft_nickname)
            
            # Отправляем личное сообщение пользователю
            await send_welcome_message(user)

            # Отправляем сообщение в лог-канал
            log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(
                    f"## Куратор <@{ctx.author.id}> добавил игрока <@{user.id}> через команду."
                )

            # Успешное добавление
            await response_channel.send(
                f"✅ Игрок <@{user.id}> успешно добавлен!",
                ephemeral=True
            )

        except Exception as e:
            error_message = f"Произошла ошибка при добавлении игрока: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            if isinstance(ctx, discord.Interaction):
                if not ctx.response.is_done():
                    await ctx.response.send_message(error_message, ephemeral=True)
                else:
                    await ctx.followup.send(error_message, ephemeral=True)
            else:
                await ctx.reply(error_message)

    @add_player.error
    async def add_player_error(self, ctx: Union[commands.Context, discord.Interaction], error: Exception):
        """Обработчик ошибок для команды add_player."""
        if isinstance(error, commands.MissingRequiredArgument):
            syntax = "`!add @пользователь никнейм`" if isinstance(ctx, commands.Context) else "`/add @пользователь никнейм`"
            response = f"Недостаточно аргументов. Используйте: {syntax}"
            
            if isinstance(ctx, discord.Interaction):
                if not ctx.response.is_done():
                    await ctx.response.send_message(response, ephemeral=True)
                else:
                    await ctx.followup.send(response, ephemeral=True)
            else:
                await ctx.reply(response)
                
        elif isinstance(error, commands.MissingAnyRole):
            response = "У вас нет необходимых прав для использования этой команды."
            if isinstance(ctx, discord.Interaction):
                if not ctx.response.is_done():
                    await ctx.response.send_message(response, ephemeral=True)
                else:
                    await ctx.followup.send(response, ephemeral=True)
            else:
                await ctx.reply(response)
        else:
            logger.error(f"Необработанная ошибка в команде add_player: {error}", exc_info=True)


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
            
            # Обновляем текст сообщения и view, добавляя причину отказа
            await interaction.message.edit(
                content=f"## Заявка игрока <@{self.discord_id}> отклонена!\n-# Причина: {self.reason.value}",
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
    discord_id: str, 
    embed: discord.Embed
) -> bool:
    """
    Создает сообщение с заявкой в указанном канале и отправляет копию пользователю.
    
    Args:
        channel: Канал Discord для отправки заявки
        discord_id: ID пользователя Discord
        embed: Embed с данными заявки
        
    Returns:
        bool: True если сообщение успешно отправлено, иначе False
    """
    try:
        # Проверяем на дубликаты
        current_time = time.time()
        recent_apps = recent_applications[discord_id]
        
        # Очищаем старые записи
        recent_apps = [t for t in recent_apps if current_time - t < DEDUP_WINDOW]
        
        # Если есть недавние заявки, пропускаем
        if recent_apps:
            logger.warning(f"Обнаружен дубликат заявки для пользователя {discord_id}. Пропускаем.")
            return False
            
        # Добавляем текущую заявку в список
        recent_apps.append(current_time)
        recent_applications[discord_id] = recent_apps

        # Продолжаем обработку заявки...
        main_fields = []
        details_fields = []
        
        for field in embed.fields:
            if field.name == 'Ваш Discord ID пользователя':
                continue
                
            field_data = {
                'name': field.name,
                'value': field.value,
                'inline': field.name in ['Ваш никнейм в Minecraft', 'Ваш возраст', 'Опыт игры в Minecraft']
            }
            
            if field_data['inline']:
                main_fields.append(field_data)
            else:
                details_fields.append(field_data)

        # Создаем embeds для канала
        embeds = []
        if main_fields:
            embeds.append(create_embed_with_fields(
                "📝 Основная информация",
                main_fields,
                embed.timestamp
            ))
        
        if details_fields:
            embeds.append(create_embed_with_fields(
                "📋 Подробная информация",
                details_fields,
                embed.timestamp
            ))

        # Отправляем заявку в канал
        view = discord.ui.View(timeout=None)
        view.add_item(ApproveButton(discord_id))
        view.add_item(RejectButton(discord_id))
        view.add_item(CandidateButton(discord_id))
        
        await channel.send(
            content=f"-# ||<@&{MODERATOR_ROLE_ID}>||\n## <@{discord_id}> отправил заявку на сервер!",
            embeds=embeds,
            view=view
        )

        # Отправляем копию заявки пользователю
        try:
            user = await channel.guild.fetch_member(int(discord_id))
            if user:
                user_embeds = []
                if main_fields:
                    user_main_embed = create_embed_with_fields(
                        "📝 Ваша заявка (основная информация)",
                        main_fields,
                        embed.timestamp
                    )
                    user_main_embed.description = "Ваша заявка успешно отправлена на рассмотрение!"
                    user_embeds.append(user_main_embed)
                
                if details_fields:
                    user_details_embed = create_embed_with_fields(
                        "📋 Ваша заявка (подробная информация)",
                        details_fields,
                        embed.timestamp
                    )
                    user_embeds.append(user_details_embed)

                await user.send(
                    content="# ✅ Ваша заявка успешно отправлена!\nОжидайте решения кураторов набора. Вы получите уведомление, когда заявка будет рассмотрена.",
                    embeds=user_embeds
                )
        except discord.Forbidden:
            logger.warning(f"Не удалось отправить личное сообщение пользователю {discord_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке копии заявки пользователю: {e}", exc_info=True)

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
            if field.name == 'Ваш никнейм в Minecraft' or field.name == 'Ваш никнейм в Minecraft:':
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
    # Создаем новую view с кнопкой "Одобрено"
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
    # Создаем новую view с кнопками
    view = discord.ui.View(timeout=None)
    
    # Кнопка "На рассмотрении" (неактивная)
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
    view.add_item(candidate_button)
    view.add_item(approve_button)
    view.add_item(reject_button)
    
    # Обновляем оригинальное сообщение, убирая упоминание роли модератора
    await message.edit(
        content=f"## Заявка игрока <@{discord_id}>",
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


# Создаем и запускаем бота
def run_bot():
    """Создает и запускает бота."""
    bot = MineBuildBot()
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))


if __name__ == '__main__':
    run_bot()


class RemoveFromWhitelistButton(discord.ui.Button):
    """Кнопка для исключения игрока из белого списка."""
    
    def __init__(self, member_id: str, nickname: str) -> None:
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Исключить",
            custom_id=f"remove_whitelist_{member_id}_{nickname}",
            emoji="❌"
        )
        
    async def callback(self, interaction: discord.Interaction) -> None:
        """Обработчик нажатия кнопки исключения."""
        # Проверяем права пользователя
        if not has_moderation_permissions(interaction.user):
            await interaction.response.send_message(
                "У вас нет прав для удаления игрока из вайтлиста. Необходимо быть администратором или модератором.", 
                ephemeral=True
            )
            return

        # Получаем идентификаторы из custom_id
        parts = self.custom_id.split('_')
        member_id = parts[2]
        nickname = '_'.join(parts[3:])  # Восстанавливаем никнейм, если он содержал подчеркивания
        
        # Отвечаем на взаимодействие сразу, чтобы не было таймаута
        await interaction.response.defer(ephemeral=True)
        
        # Удаляем из белого списка через RCON
        success = await remove_from_whitelist(nickname)
        
        # Обновляем сообщение
        view = discord.ui.View(timeout=None)
        button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Исключён",
            emoji="✅",
            disabled=True,
            custom_id=f"removed_{member_id}"
        )
        view.add_item(button)
        
        await interaction.message.edit(
            content=f"## Игрок <@{member_id}> с ником `{nickname}` вышел из дискорд сервера!\n> - Игрок исключен из белого списка.",
            view=view
        )
        
        # Отправляем сообщение в лог-канал
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(
                f"# Куратор <@{interaction.user.id}> исключил игрока {nickname} из белого списка после его выхода из сервера."
            )
        
        # Отчет модератору
        if success:
            await interaction.followup.send(
                f"Игрок {nickname} успешно удален из белого списка.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"Произошла ошибка при удалении игрока {nickname} из белого списка. Проверьте состояние сервера.",
                ephemeral=True
            )


class IgnoreLeaveButton(discord.ui.Button):
    """Кнопка для игнорирования выхода игрока."""
    
    def __init__(self, member_id: str, nickname: str) -> None:
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Игнорировать",
            custom_id=f"ignore_leave_{member_id}_{nickname}",
            emoji="🔕"
        )
        
    async def callback(self, interaction: discord.Interaction) -> None:
        """Обработчик нажатия кнопки игнорирования."""
        # Проверяем права пользователя
        if not has_moderation_permissions(interaction.user):
            await interaction.response.send_message(
                "У вас нет прав для игнорирования уведомлений. Необходимо быть администратором или модератором.", 
                ephemeral=True
            )
            return

        # Получаем идентификаторы из custom_id
        parts = self.custom_id.split('_')
        member_id = parts[2]
        nickname = '_'.join(parts[3:])  # Восстанавливаем никнейм, если он содержал подчеркивания
        
        # Обновляем сообщение
        view = discord.ui.View(timeout=None)
        button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Проигнорировано",
            emoji="🔕",
            disabled=True,
            custom_id=f"ignored_{member_id}"
        )
        view.add_item(button)
        
        await interaction.message.edit(
            content=f"## Игрок <@{member_id}> с ником `{nickname}` вышел из дискорд сервера!\n> - Уведомление проигнорировано.",
            view=view
        )
        
        await interaction.response.defer(ephemeral=True)  # Скрытое подтверждение действия


async def send_member_leave_notification(channel: discord.TextChannel, member_id: int, nickname: str) -> None:
    """
    Отправляет уведомление о выходе пользователя с кнопками действий.
    
    Args:
        channel: Канал для отправки уведомления
        member_id: ID пользователя Discord
        nickname: Никнейм пользователя
    """
    # Создаем view с кнопками
    view = discord.ui.View(timeout=None)
    
    # Добавляем кнопки
    view.add_item(RemoveFromWhitelistButton(str(member_id), nickname))
    view.add_item(IgnoreLeaveButton(str(member_id), nickname))
    
    # Отправляем сообщение
    await channel.send(
        content=f"## Игрок <@{member_id}> с ником `{nickname}` вышел из дискорд сервера!\n> - Желаете его исключить из белого списка?",
        view=view
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
        logger.error(f"Сервер Minecraft недоступен. Не удалось удалить игрока {minecraft_nickname} из белого списка.")
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
            logger.info(f"RCON response for whitelist removal: {clean_response}")
            
            # Проверяем успешность операции
            success = "removed" in clean_response.lower() or "удален" in clean_response.lower()
            return success
            
    except (socket.timeout, ConnectionRefusedError) as e:
        error_message = "Таймаут при подключении к серверу" if isinstance(e, socket.timeout) else "Соединение отклонено сервером"
        logger.error(f"{error_message}: {e}")
        return False
    except Exception as e:
        logger.error(f"Ошибка RCON при удалении из белого списка: {e}", exc_info=True)
        return False