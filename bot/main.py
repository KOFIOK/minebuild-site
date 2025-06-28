"""
Основной класс Discord бота MineBuild
"""

import os
import logging
import discord
from discord.ext import commands

from .config import (
    setup_logging,
    DISCORD_TOKEN,
    GUILD_ID,
    WHITELIST_ROLE_ID,
    LOG_CHANNEL_ID,
    DONATION_CHANNEL_ID,
    DONATOR_ROLE_ID
)
from .ui.views import (
    PersistentApplicationView, 
    PersistentMemberLeaveView, 
    PersistentViewManager
)
from .utils.minecraft import execute_minecraft_command

# Настройка логирования
logger = setup_logging()


async def send_member_leave_notification(channel: discord.TextChannel, member_id: int, nickname: str) -> None:
    """
    Отправляет уведомление о выходе пользователя с кнопками действий.
    
    Args:
        channel: Канал для отправки уведомления
        member_id: ID пользователя Discord
        nickname: Никнейм пользователя
    """
    # Создаем view с кнопками
    view = PersistentMemberLeaveView(str(member_id), nickname)
    
    # Отправляем сообщение
    await channel.send(
        content=f"## Игрок <@{member_id}> с ником `{nickname}` вышел из дискорд сервера!\n> - Желаете его исключить из белого списка?",
        view=view
    )


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
        # Канал для заявок (будет установлен в on_ready)
        self.channel_for_applications = None
        
        # Менеджер персистентных представлений
        self.persistent_view_manager = PersistentViewManager(self)
        
    async def setup_hook(self) -> None:
        """Хук настройки для инициализации необходимых компонентов."""
        # Загружаем расширения (cogs)
        try:
            await self.load_extension("bot.cogs.admin")
            logger.info("Загружен модуль admin commands")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модуля admin: {e}")
        
        # Регистрируем персистентные представления
        self.persistent_view_manager.register_view(PersistentApplicationView, "ApplicationView")
        self.persistent_view_manager.register_view(PersistentMemberLeaveView, "MemberLeaveView")
        
        # Добавляем базовое представление для заявок (можно без кнопок)
        self.add_view(PersistentApplicationView())
        
        # Синхронизируем команды для конкретного сервера
        try:
            if GUILD_ID:
                guild = discord.Object(id=GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"Команды синхронизированы для сервера {GUILD_ID}")
            else:
                logger.warning("GUILD_ID не настроен, команды будут синхронизированы глобально")
                await self.tree.sync()
        except Exception as e:
            logger.error(f"Ошибка при синхронизации команд: {e}")
            await self.tree.sync()  # Fallback к глобальной синхронизации
        
    async def on_ready(self) -> None:
        """Вызывается когда бот успешно подключился к Discord."""
        logger.info(f"Бот {self.user} запущен и готов к работе!")
        
        # Находим канал для заявок
        application_channel_id = 1360709668770418789  # ID канала для заявок
        
        try:
            self.channel_for_applications = self.get_channel(application_channel_id)
            if self.channel_for_applications:
                logger.info(f"Канал для заявок найден: {self.channel_for_applications.name}")
            else:
                logger.warning(f"Канал для заявок с ID {application_channel_id} не найден")
        except Exception as e:
            logger.error(f"Ошибка при поиске канала для заявок: {e}")
        
        # Восстанавливаем персистентные представления из существующих сообщений
        try:
            await self.persistent_view_manager.restore_views_from_messages()
            logger.info("Персистентные представления восстановлены")
        except Exception as e:
            logger.error(f"Ошибка при восстановлении персистентных представлений: {e}")
            
        logger.info("Бот полностью готов к работе!")

    async def on_member_remove(self, member: discord.Member) -> None:
        """Вызывается когда пользователь покидает сервер."""
        try:
            # Проверяем, есть ли у пользователя роль вайтлиста
            has_whitelist = any(role.id == WHITELIST_ROLE_ID for role in member.roles)
            
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
    
    async def handle_donation(self, nickname: str, amount: int) -> bool:
        """
        Обрабатывает донат в зависимости от суммы и выполняет соответствующие действия:
        - Благодарственное сообщение для всех донатов от 100₽
        - Выдача роли донатера за донаты от 300₽
        - Установка суффикса через RCON за донаты от 500₽
        
        Args:
            nickname: Никнейм игрока
            amount: Сумма доната в рублях
            
        Returns:
            bool: True если обработка прошла успешно, False в случае ошибки
        """
        try:
            # Получаем канал для отправки сообщений о донатах
            donation_channel = self.get_channel(DONATION_CHANNEL_ID)
            if not donation_channel:
                logger.error(f"Не удалось найти канал для донатов с ID {DONATION_CHANNEL_ID}")
                return False

            logger.info(f"Обработка доната: игрок={nickname}, сумма={amount}₽")

            # Создаем красивое embed-сообщение с благодарностью
            embed = discord.Embed(
                title="Новый донат!",
                description=f"**{nickname}** - спасибо за **{amount} ₽** переводом",
                color=0x68caff  # Голубой цвет (68caff)
            )
            
            embed.set_footer(text="MineBuild Donations")
            embed.timestamp = discord.utils.utcnow()

            # Добавляем информацию о наградах
            rewards = []
            if amount >= 100:
                rewards.append("✅ Благодарственное сообщение")
            
            if amount >= 300:
                rewards.append("✅ Роль Благодеятеля в Discord")
            
            if amount >= 500:
                rewards.append("✅ Уникальный суффикс в игре")
            
            if amount >= 1000:
                rewards.append("✅ Индивидуальный суффикс в игре")
            
            if rewards:
                embed.add_field(name="Награды", value="\n".join(rewards), inline=False)

            # Отправляем сообщение о донате
            await donation_channel.send(embed=embed)
            logger.info(f"Отправлено сообщение о донате игрока {nickname} на сумму {amount}₽")

            # Если сумма доната 300₽ и больше - выдаем роль Благодеятеля
            if amount >= 300:
                # Получаем сервер
                guild = donation_channel.guild
                
                # Найти пользователя по нику
                member = None
                for m in guild.members:
                    member_nick = m.nick or m.name
                    if member_nick.lower() == nickname.lower():
                        member = m
                        break
                
                if member:
                    # Выдаем роль Благодеятеля
                    donator_role = guild.get_role(DONATOR_ROLE_ID)
                    if donator_role:
                        await member.add_roles(donator_role)
                        logger.info(f"Выдана роль Благодеятеля пользователю {nickname}")
                    else:
                        logger.error(f"Не удалось найти роль Благодеятеля с ID {DONATOR_ROLE_ID}")
                else:
                    logger.warning(f"Не удалось найти пользователя с ником {nickname} для выдачи роли Благодеятеля")

            # Если сумма доната 500₽ и больше - выдаем суффикс через RCON
            if amount >= 500:
                # Выполняем команду на сервере Minecraft через RCON
                success = await execute_minecraft_command(f"lp user {nickname} permission set title.u.donate")
                
                if success:
                    logger.info(f"Выдан суффикс донатера игроку {nickname}")
                else:
                    logger.error(f"Не удалось выдать суффикс донатера игроку {nickname}")
                    
                    # Отправляем сообщение о проблеме
                    error_embed = discord.Embed(
                        title="⚠️ Внимание!",
                        description=f"Не удалось выдать суффикс игроку **{nickname}**. Требуется ручная выдача.",
                        color=0xFF0000
                    )
                    await donation_channel.send(embed=error_embed)

            return True

        except Exception as e:
            logger.error(f"Ошибка при обработке доната: {e}", exc_info=True)
            return False


def run_bot():
    """Создает и запускает бота."""
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN не установлен в переменных окружения!")
        return
        
    bot = MineBuildBot()
    bot.run(DISCORD_TOKEN)


if __name__ == '__main__':
    run_bot()
