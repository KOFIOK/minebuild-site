"""
Кнопки для управления заявками на сервер MineBuild
"""

import asyncio
import logging
import discord
from typing import Optional

from .base import BaseActionButton
from .modals import RejectModal
from ..config import (
    WHITELIST_ROLE_ID, 
    CANDIDATE_ROLE_ID, 
    LOG_CHANNEL_ID, 
    CANDIDATE_CHAT_ID
)
from ..utils.helpers import (
    has_moderation_permissions,
    extract_minecraft_nickname,
    process_approval,
    update_approval_message,
    update_candidate_message,
    send_welcome_message
)
from ..utils.api import update_web_application_status, clear_web_application_status

logger = logging.getLogger("MineBuildBot.UI.Buttons")


class ApproveButton(BaseActionButton):
    """Кнопка для одобрения заявки."""
    
    def __init__(self, discord_id: str, is_candidate: bool = False) -> None:
        super().__init__(
            style=discord.ButtonStyle.green,
            label="Одобрить",
            custom_id=f"approve_{discord_id}_{is_candidate}",
            emoji="✅"
        )
        self.discord_id = discord_id
        self.is_candidate = is_candidate
    
    @classmethod
    def from_custom_id(cls, custom_id: str):
        """Создает кнопку из custom_id для восстановления после рестарта."""
        parts = custom_id.split('_')
        if len(parts) >= 3 and parts[0] == 'approve':
            discord_id = parts[1]
            is_candidate = parts[2].lower() in ('true', 'True')
            return cls(discord_id, is_candidate)
        return None
        
    async def process_action(self, interaction: discord.Interaction, original_message: discord.Message) -> None:
        """Обработчик нажатия кнопки одобрения."""
        # Проверяем права пользователя
        if not has_moderation_permissions(interaction.user):
            await interaction.response.send_message(
                "У вас нет прав для одобрения заявок. Необходимо быть администратором или модератором.", 
                ephemeral=True
            )
            return
            
        # Получаем роли
        whitelist_role = interaction.guild.get_role(WHITELIST_ROLE_ID)
        candidate_role = interaction.guild.get_role(CANDIDATE_ROLE_ID)
        
        if not whitelist_role:
            await interaction.response.send_message("Роль для вайтлиста не найдена.", ephemeral=True)
            return

        try:
            # Получаем объект участника
            member = await interaction.guild.fetch_member(int(self.discord_id))
            if not member:
                await interaction.response.send_message("Пользователь не найден.", ephemeral=True)
                return

            # Отвечаем на взаимодействие сразу, чтобы не было таймаута
            await interaction.response.defer(ephemeral=True)

            # Отправляем сообщение в лог-канал
            log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(
                    f"## Куратор <@{interaction.user.id}> одобрил [заявку]({original_message.jump_url})."
                )

            # Получаем никнейм из заявки
            logger.info(f"Попытка извлечь никнейм из заявки пользователя {self.discord_id}")
            minecraft_nickname = extract_minecraft_nickname(original_message.embeds)
            
            if not minecraft_nickname:
                logger.error(f"❌ Не удалось найти никнейм в заявке пользователя {self.discord_id}")
                await interaction.followup.send(
                    "❌ Не удалось найти никнейм в заявке. Проверьте правильность заполнения заявки.",
                    ephemeral=True
                )
                return
            
            logger.info(f"✅ Никнейм найден: '{minecraft_nickname}' для пользователя {self.discord_id}")
                
            # Если это кандидат, снимаем с него роль кандидата
            if self.is_candidate and candidate_role and candidate_role in member.roles:
                await member.remove_roles(candidate_role)
                logger.info(f"Снята роль кандидата с пользователя {self.discord_id} при одобрении")
            
            # Обрабатываем одобрение (добавление в whitelist, изменение никнейма)
            await process_approval(interaction, member, minecraft_nickname)
                
            # Добавляем роль вайтлиста
            await member.add_roles(whitelist_role)
            
            # Обновляем сообщение
            await update_approval_message(original_message, self.discord_id)
            
            # Очищаем статус на веб-сайте - пользователь сможет подать заявку заново
            await clear_web_application_status(self.discord_id)
            
            # Отправляем личное сообщение пользователю
            await send_welcome_message(member)
            
            # Сообщаем модератору об успешной обработке
            await interaction.followup.send(
                f"✅ Заявка игрока <@{self.discord_id}> успешно одобрена!",
                ephemeral=True
            )
            
        except discord.NotFound:
            logger.error(f"Пользователь {self.discord_id} не найден на сервере")
            await interaction.followup.send(
                f"❌ Пользователь с ID {self.discord_id} не найден на сервере.",
                ephemeral=True
            )
        except discord.Forbidden:
            logger.error(f"Недостаточно прав для добавления роли пользователю {self.discord_id}")
            await interaction.followup.send(
                f"❌ Недостаточно прав для добавления роли пользователю <@{self.discord_id}>.",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Ошибка при одобрении заявки: {e}", exc_info=True)
            await interaction.followup.send(f"Произошла ошибка: {str(e)}", ephemeral=True)


class RejectButton(BaseActionButton):
    """Кнопка для отклонения заявки."""
    
    def __init__(self, discord_id: str, is_candidate: bool = False) -> None:
        super().__init__(
            style=discord.ButtonStyle.red,
            label="Отказать",
            custom_id=f"reject_{discord_id}_{is_candidate}",
            emoji="❎"
        )
        self.discord_id = discord_id
        self.is_candidate = is_candidate
    
    @classmethod
    def from_custom_id(cls, custom_id: str):
        """Создает кнопку из custom_id для восстановления после рестарта."""
        parts = custom_id.split('_')
        if len(parts) >= 3 and parts[0] == 'reject':
            discord_id = parts[1]
            is_candidate = parts[2].lower() in ('true', 'True')
            return cls(discord_id, is_candidate)
        return None
    
    async def callback(self, interaction: discord.Interaction) -> None:
        """Переопределенный обработчик - НЕ блокирует кнопки до отправки модального окна."""
        try:
            # Сохраняем ссылку на оригинальное сообщение
            original_message = interaction.message
            
            # Вызываем основной обработчик действия БЕЗ блокировки кнопок
            await self.process_action(interaction, original_message)
                
        except Exception as e:
            logger.error(f"Ошибка при обработке нажатия кнопки отказа: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Произошла ошибка при обработке запроса. Попробуйте снова.", 
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "Произошла ошибка при обработке запроса. Попробуйте снова.",
                    ephemeral=True
                )
        
    async def process_action(self, interaction: discord.Interaction, original_message: discord.Message) -> None:
        """Обработчик нажатия кнопки отказа."""
        # Проверяем права пользователя
        if not has_moderation_permissions(interaction.user):
            await interaction.response.send_message(
                "У вас нет прав для отказа заявок. Необходимо быть администратором или модератором.", 
                ephemeral=True
            )
            return

        # Получаем URL сообщения
        message_url = original_message.jump_url
        
        # Показываем модальное окно для ввода причины
        # НЕ БЛОКИРУЕМ кнопки до отправки модального окна
        try:
            await interaction.response.send_modal(RejectModal(self.discord_id, message_url, self.is_candidate))
        except Exception as e:
            logger.error(f"Ошибка при вызове модального окна: {e}", exc_info=True)
            await interaction.response.send_message(
                "Произошла ошибка при открытии формы отказа. Попробуйте снова.",
                ephemeral=True
            )


class CandidateButton(BaseActionButton):
    """Кнопка для перевода в кандидаты."""
    
    def __init__(self, discord_id: str) -> None:
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="В кандидаты",
            custom_id=f"candidate_{discord_id}",
            emoji="🔍"
        )
        self.discord_id = discord_id
    
    @classmethod
    def from_custom_id(cls, custom_id: str):
        """Создает кнопку из custom_id для восстановления после рестарта."""
        parts = custom_id.split('_')
        if len(parts) >= 2 and parts[0] == 'candidate':
            discord_id = parts[1]
            return cls(discord_id)
        return None
        
    async def process_action(self, interaction: discord.Interaction, original_message: discord.Message) -> None:
        """Обработчик нажатия кнопки перевода в кандидаты."""
        # Проверяем права пользователя
        if not has_moderation_permissions(interaction.user):
            await interaction.response.send_message(
                "У вас нет прав для управления кандидатами. Необходимо быть администратором или модератором.", 
                ephemeral=True
            )
            return

        # Получаем роль кандидата
        candidate_role = interaction.guild.get_role(CANDIDATE_ROLE_ID)
        
        if not candidate_role:
            await interaction.response.send_message("Роль кандидата не найдена.", ephemeral=True)
            return

        try:
            # Получаем объект участника
            member = await interaction.guild.fetch_member(int(self.discord_id))
            if not member:
                await interaction.response.send_message("Пользователь не найден.", ephemeral=True)
                return

            # Отвечаем на взаимодействие сразу, чтобы не было таймаута
            await interaction.response.defer(ephemeral=True)

            # Получаем никнейм из заявки
            minecraft_nickname = extract_minecraft_nickname(original_message.embeds)
            
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
            await update_candidate_message(original_message, self.discord_id)
            
            # Обновляем статус на веб-сайте
            await update_web_application_status(self.discord_id, 'candidate')
            
            # Отправляем сообщение в канал кандидатов
            candidate_channel = interaction.guild.get_channel(CANDIDATE_CHAT_ID)
            if candidate_channel:
                await candidate_channel.send(
                    f"# Привет, <@{self.discord_id}>!\n"
                    f"Твоя заявка была отправлена на рассмотрение куратором <@{interaction.user.id}>.\n"
                    f"Ты получил временную роль кандидата, которая предоставляет доступ к этому каналу.\n"
                    f"В ближайшее время с тобой свяжутся для обсуждения деталей."
                )
            
            # Отправляем сообщение в лог
            log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(
                    f"## Куратор <@{interaction.user.id}> перевел игрока <@{self.discord_id}> в кандидаты. "
                    f"[Ссылка на заявку]({original_message.jump_url})"
                )
            
            # Отправляем сообщение куратору
            await interaction.followup.send(
                f"Игрок <@{self.discord_id}> успешно переведен в кандидаты и получил соответствующую роль.",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Ошибка при переводе в кандидаты: {e}", exc_info=True)
            await interaction.followup.send(f"Произошла ошибка: {str(e)}", ephemeral=True)


class RemoveFromWhitelistButton(BaseActionButton):
    """Кнопка для исключения игрока из белого списка."""
    
    def __init__(self, member_id: str, nickname: str) -> None:
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Исключить",
            custom_id=f"remove_whitelist_{member_id}_{nickname}",
            emoji="❌"
        )
        self.member_id = member_id
        self.nickname = nickname
    
    @classmethod
    def from_custom_id(cls, custom_id: str):
        """Создает кнопку из custom_id для восстановления после рестарта."""
        parts = custom_id.split('_')
        if len(parts) >= 4 and '_'.join(parts[:2]) == 'remove_whitelist':
            member_id = parts[2]
            nickname = '_'.join(parts[3:])  # Никнейм может содержать подчеркивания
            return cls(member_id, nickname)
        return None
        
    async def process_action(self, interaction: discord.Interaction, original_message: discord.Message) -> None:
        """Обработчик нажатия кнопки исключения."""
        from ..utils.minecraft import remove_from_whitelist
        
        # Проверяем права пользователя
        if not has_moderation_permissions(interaction.user):
            await interaction.response.send_message(
                "У вас нет прав для удаления игрока из вайтлиста. Необходимо быть администратором или модератором.", 
                ephemeral=True
            )
            return
        
        # Отвечаем на взаимодействие сразу, чтобы не было таймаута
        await interaction.response.defer(ephemeral=True)
        
        # Удаляем из белого списка через RCON
        success = await remove_from_whitelist(self.nickname)
        
        # Обновляем сообщение
        view = discord.ui.View(timeout=None)
        button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Исключён",
            emoji="✅",
            disabled=True,
            custom_id=f"removed_{self.member_id}"
        )
        view.add_item(button)
        
        await original_message.edit(
            content=f"## Игрок <@{self.member_id}> с ником `{self.nickname}` вышел из дискорд сервера!\n> - Игрок исключен из белого списка.",
            view=view
        )
        
        # Отправляем сообщение в лог-канал
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(
                f"# Куратор <@{interaction.user.id}> исключил игрока {self.nickname} из белого списка после его выхода из сервера."
            )
        
        # Отчет модератору
        if success:
            await interaction.followup.send(
                f"✅ Игрок {self.nickname} успешно исключен из белого списка.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"⚠️ Не удалось исключить игрока {self.nickname} из белого списка. Проверьте состояние сервера.",
                ephemeral=True
            )


class IgnoreLeaveButton(BaseActionButton):
    """Кнопка для игнорирования выхода игрока."""
    
    def __init__(self, member_id: str, nickname: str) -> None:
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Игнорировать",
            custom_id=f"ignore_leave_{member_id}_{nickname}",
            emoji="🔕"
        )
        self.member_id = member_id
        self.nickname = nickname
    
    @classmethod
    def from_custom_id(cls, custom_id: str):
        """Создает кнопку из custom_id для восстановления после рестарта."""
        parts = custom_id.split('_')
        if len(parts) >= 4 and '_'.join(parts[:2]) == 'ignore_leave':
            member_id = parts[2]
            nickname = '_'.join(parts[3:])  # Никнейм может содержать подчеркивания
            return cls(member_id, nickname)
        return None
        
    async def process_action(self, interaction: discord.Interaction, original_message: discord.Message) -> None:
        """Обработчик нажатия кнопки игнорирования."""
        # Проверяем права пользователя
        if not has_moderation_permissions(interaction.user):
            await interaction.response.send_message(
                "У вас нет прав для управления уведомлениями. Необходимо быть администратором или модератором.",
                ephemeral=True
            )
            return
        
        # Отвечаем на взаимодействие
        await interaction.response.defer(ephemeral=True)
        
        # Обновляем сообщение
        view = discord.ui.View(timeout=None)
        button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Проигнорировано",
            emoji="🔕",
            disabled=True,
            custom_id=f"ignored_{self.member_id}"
        )
        view.add_item(button)
        
        await original_message.edit(
            content=f"## Игрок <@{self.member_id}> с ником `{self.nickname}` вышел из дискорд сервера!\n> - Уведомление проигнорировано.",
            view=view
        )
        
        await interaction.followup.send(
            f"✅ Уведомление о выходе игрока {self.nickname} проигнорировано.",
            ephemeral=True
        )
