"""
Основной класс Discord бота MineBuild
"""

import os
import logging
import signal
import asyncio
import discord
from discord.ext import commands

from .config import (
    setup_logging,
    DISCORD_TOKEN,
    GUILD_ID
)
from .config_manager import (
    get_whitelist_role_id,
    get_log_channel_id,
    get_donation_channel_id,
    get_donator_role_id
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
                
                # Получаем количество команд перед синхронизацией
                commands_before = len(self.tree.get_commands())
                logger.info(f"Подготовка к синхронизации {commands_before} команд для сервера {GUILD_ID}")
                
                synced = await self.tree.sync(guild=guild)
                logger.info(f"✅ Успешно синхронизировано {len(synced)} команд для сервера {GUILD_ID}")
                
                # Выводим список синхронизированных команд
                if synced:
                    command_names = [cmd.name for cmd in synced]
                    logger.info(f"Синхронизированные команды: {', '.join(command_names)}")
                else:
                    logger.warning("Нет команд для синхронизации")
                    
            else:
                logger.warning("GUILD_ID не настроен, команды будут синхронизированы глобально")
                commands_before = len(self.tree.get_commands())
                logger.info(f"Подготовка к глобальной синхронизации {commands_before} команд")
                
                synced = await self.tree.sync()
                logger.info(f"✅ Успешно синхронизировано {len(synced)} команд глобально")
                
                if synced:
                    command_names = [cmd.name for cmd in synced]
                    logger.info(f"Синхронизированные команды: {', '.join(command_names)}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при синхронизации команд: {e}")
            try:
                logger.info("Попытка fallback к глобальной синхронизации...")
                synced = await self.tree.sync()  # Fallback к глобальной синхронизации
                logger.info(f"✅ Fallback: синхронизировано {len(synced)} команд глобально")
            except Exception as fallback_error:
                logger.error(f"❌ Fallback также не удался: {fallback_error}")
        
    async def on_ready(self) -> None:
        """Вызывается когда бот успешно подключился к Discord."""
        logger.info(f"🤖 Бот {self.user} запущен и готов к работе!")
        
        # Выводим итоговую информацию о командах
        total_commands = len(self.tree.get_commands())
        logger.info(f"📋 Доступно команд в дереве: {total_commands}")
        
        # Выводим информацию о загруженных расширениях
        loaded_extensions = list(self.extensions.keys())
        if loaded_extensions:
            logger.info(f"🔧 Загруженные расширения: {', '.join(loaded_extensions)}")
        else:
            logger.warning("⚠️ Нет загруженных расширений")
        
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
            has_whitelist = any(role.id == get_whitelist_role_id() for role in member.roles)
            
            if has_whitelist:
                # Получаем никнейм пользователя
                nickname = member.nick or member.name
                
                # Отправляем уведомление в лог-канал
                log_channel = self.get_channel(get_log_channel_id())
                if log_channel:
                    await send_member_leave_notification(log_channel, member.id, nickname)
                    logger.info(f"Отправлено уведомление о выходе пользователя {member.id} с ролью вайтлиста")
                else:
                    logger.error(f"Не удалось найти канал логов {get_log_channel_id()}")
            
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
            donation_channel = self.get_channel(get_donation_channel_id())
            if not donation_channel:
                logger.error(f"Не удалось найти канал для донатов с ID {get_donation_channel_id()}")
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
                    donator_role = guild.get_role(get_donator_role_id())
                    if donator_role:
                        await member.add_roles(donator_role)
                        logger.info(f"Выдана роль Благодеятеля пользователю {nickname}")
                    else:
                        logger.error(f"Не удалось найти роль Благодеятеля с ID {get_donator_role_id()}")
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

    async def close(self) -> None:
        """Корректно завершает работу бота, освобождая все ресурсы."""
        logger.info("🔄 Начинается корректное завершение работы бота...")
        
        try:
            # Закрываем персистентные представления
            if hasattr(self, 'persistent_view_manager'):
                logger.info("Завершение работы менеджера персистентных представлений...")
                # Здесь можно добавить cleanup для view manager, если нужно
            
            # Получаем все задачи, исключая текущую
            current_task = asyncio.current_task()
            all_tasks = [task for task in asyncio.all_tasks() if not task.done() and task != current_task]
            
            if all_tasks:
                logger.info(f"Ожидание завершения {len(all_tasks)} задач...")
                
                # Группируем задачи по типам для более безопасной отмены
                cancellable_tasks = []
                system_tasks = []
                
                for task in all_tasks:
                    task_name = getattr(task, 'get_name', lambda: 'unknown')()
                    if any(keyword in task_name.lower() for keyword in ['timeout', 'sleep', 'wait', 'connection']):
                        system_tasks.append(task)
                    else:
                        cancellable_tasks.append(task)
                
                # Сначала пытаемся корректно завершить обычные задачи
                if cancellable_tasks:
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*cancellable_tasks, return_exceptions=True),
                            timeout=5.0
                        )
                        logger.info(f"✅ Корректно завершено {len(cancellable_tasks)} обычных задач")
                    except asyncio.TimeoutError:
                        logger.warning(f"⏰ Таймаут при ожидании {len(cancellable_tasks)} обычных задач, отменяем...")
                        for task in cancellable_tasks:
                            if not task.done():
                                task.cancel()
                
                # Отдельно обрабатываем системные задачи
                if system_tasks:
                    logger.info(f"Отмена {len(system_tasks)} системных задач...")
                    for task in system_tasks:
                        if not task.done():
                            try:
                                task.cancel()
                            except Exception as e:
                                logger.debug(f"Ошибка при отмене системной задачи: {e}")
                    
                    # Даем короткое время на завершение
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*system_tasks, return_exceptions=True),
                            timeout=2.0
                        )
                    except asyncio.TimeoutError:
                        logger.debug("Системные задачи не завершились в отведенное время")
            
        except asyncio.TimeoutError:
            logger.warning("⏰ Таймаут при ожидании завершения задач, принудительно завершаем...")
        except RecursionError:
            logger.warning("🔄 Обнаружена рекурсивная отмена задач, пропускаем...")
        except Exception as e:
            logger.error(f"Ошибка при завершении работы: {e}", exc_info=True)
        finally:
            # Вызываем родительский метод close
            try:
                await super().close()
                logger.info("✅ Бот корректно завершил работу")
            except Exception as e:
                logger.error(f"Ошибка при вызове super().close(): {e}", exc_info=True)

def run_bot():
    """Создает и запускает бота с корректной обработкой завершения работы."""
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN не установлен в переменных окружения!")
        return
    
    # Создаем бота
    bot = MineBuildBot()
    
    # Флаг для graceful shutdown
    shutdown_event = asyncio.Event()
    
    async def shutdown_handler():
        """Обработчик корректного завершения работы."""
        logger.info("🛑 Получен сигнал завершения работы...")
        shutdown_event.set()
        
        # Корректно закрываем бота
        if not bot.is_closed():
            await bot.close()
    
    def signal_handler(signum, frame):
        """Обработчик сигналов системы."""
        logger.info(f"Получен сигнал {signum}, инициируем корректное завершение...")
        
        # Создаем задачу для graceful shutdown
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(shutdown_handler())
        else:
            asyncio.run(shutdown_handler())
    
    # Регистрируем обработчики сигналов
    try:
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)  # Terminate
    except Exception as e:
        logger.warning(f"Не удалось зарегистрировать обработчики сигналов: {e}")
    
    # Запускаем бота с обработкой исключений
    try:
        logger.info("🚀 Запуск бота...")
        bot.run(DISCORD_TOKEN, log_handler=None)  # Отключаем стандартный log handler
    except KeyboardInterrupt:
        logger.info("⌨️ Получен KeyboardInterrupt, завершаем работу...")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при работе бота: {e}", exc_info=True)
    finally:
        logger.info("🔚 Работа бота завершена")


async def run_bot_async():
    """Асинхронная версия запуска бота для лучшего контроля lifecycle."""
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN не установлен в переменных окружения!")
        return
    
    bot = MineBuildBot()
    
    try:
        logger.info("🚀 Асинхронный запуск бота...")
        await bot.start(DISCORD_TOKEN)
    except asyncio.CancelledError:
        logger.info("🛑 Запуск бота был отменен")
        raise  # Передаем CancelledError выше
    except KeyboardInterrupt:
        logger.info("⌨️ Получен KeyboardInterrupt в run_bot_async...")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}", exc_info=True)
    finally:
        if not bot.is_closed():
            logger.info("🔄 Корректное завершение работы бота...")
            try:
                await bot.close()
            except Exception as close_error:
                logger.error(f"Ошибка при закрытии бота: {close_error}", exc_info=True)
        logger.info("🔚 run_bot_async завершен")


def run_bot_with_signal_handling():
    """Запуск бота с улучшенной обработкой сигналов через asyncio."""
    async def main():
        bot = None
        
        try:
            # Создание задачи для бота
            bot_task = asyncio.create_task(run_bot_async())
            
            # Обработчик сигналов
            def signal_handler():
                logger.info("🛑 Получен сигнал завершения, останавливаем бота...")
                if not bot_task.done():
                    bot_task.cancel()
            
            # Регистрируем обработчики сигналов для asyncio
            if os.name != 'nt':  # Unix-like системы
                loop = asyncio.get_running_loop()
                loop.add_signal_handler(signal.SIGINT, signal_handler)
                loop.add_signal_handler(signal.SIGTERM, signal_handler)
            
            await bot_task
            
        except asyncio.CancelledError:
            logger.info("📛 Задача бота была отменена")
        except KeyboardInterrupt:
            logger.info("⌨️ KeyboardInterrupt в main()")
        except Exception as e:
            logger.error(f"❌ Ошибка в main(): {e}", exc_info=True)
        finally:
            # Принудительная очистка оставшихся задач
            try:
                pending = [task for task in asyncio.all_tasks() if not task.done() and task != asyncio.current_task()]
                if pending:
                    logger.info(f"🧹 Очистка {len(pending)} оставшихся задач...")
                    for task in pending:
                        if not task.done():
                            task.cancel()
                    
                    # Ждем короткое время на завершение
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*pending, return_exceptions=True),
                            timeout=2.0
                        )
                    except asyncio.TimeoutError:
                        logger.debug("Некоторые задачи не завершились в отведенное время")
                        
            except Exception as cleanup_error:
                logger.debug(f"Ошибка при финальной очистке: {cleanup_error}")
    
    try:
        if os.name == 'nt':  # Windows
            # В Windows используем стандартный подход
            asyncio.run(main())
        else:
            # В Unix-like системах можем использовать более продвинутый подход
            asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⌨️ Итоговый KeyboardInterrupt перехвачен")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в run_bot_with_signal_handling: {e}", exc_info=True)


if __name__ == '__main__':
    run_bot_with_signal_handling()
