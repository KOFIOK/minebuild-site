"""
Discord UI Views для бота MineBuild
"""

import logging
import discord
from .buttons import (
    ApproveButton, RejectButton, CandidateButton,
    RemoveFromWhitelistButton, IgnoreLeaveButton
)

logger = logging.getLogger("MineBuildBot.UI.Views")


class PersistentApplicationView(discord.ui.View):
    """Персистентное представление для заявок."""
    
    def __init__(self) -> None:
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Загрузка...",
        style=discord.ButtonStyle.secondary,
        custom_id="placeholder_button",
        disabled=True
    )
    async def placeholder_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Заглушка - эта кнопка не должна вызываться."""
        await interaction.response.send_message("Ошибка: заглушка кнопки была нажата", ephemeral=True)

    @staticmethod
    def create_for_application(discord_id: str, is_candidate: bool = False) -> 'PersistentApplicationView':
        """
        Создает View с кнопками для конкретной заявки.
        
        Args:
            discord_id: ID пользователя Discord
            is_candidate: Является ли пользователь кандидатом
            
        Returns:
            PersistentApplicationView: View с соответствующими кнопками
        """
        view = PersistentApplicationView()
        view.clear_items()  # Удаляем заглушку
        
        # Добавляем кнопки для заявки
        view.add_item(ApproveButton(discord_id, is_candidate))
        view.add_item(RejectButton(discord_id, is_candidate))
        
        # Кнопка кандидата только для обычных заявок
        if not is_candidate:
            view.add_item(CandidateButton(discord_id))
            
        return view

    @staticmethod
    def create_for_candidate(discord_id: str) -> 'PersistentApplicationView':
        """
        Создает View с кнопками для кандидата.
        
        Args:
            discord_id: ID пользователя Discord
            
        Returns:
            PersistentApplicationView: View с кнопками для кандидата
        """
        view = PersistentApplicationView()
        view.clear_items()  # Удаляем заглушку
        
        # Кнопка "На рассмотрении" (неактивная)
        candidate_button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="На рассмотрении",
            emoji="🔍",
            disabled=True,
            custom_id=f"candidate_disabled_{discord_id}"
        )
        
        # Добавляем кнопки в нужном порядке
        view.add_item(candidate_button)
        view.add_item(ApproveButton(discord_id, is_candidate=True))
        view.add_item(RejectButton(discord_id, is_candidate=True))
            
        return view


class PersistentMemberLeaveView(discord.ui.View):
    """Персистентное представление для уведомлений о выходе участников."""
    
    def __init__(self, member_id: str = None, nickname: str = None) -> None:
        super().__init__(timeout=None)
        
        if member_id and nickname:
            self.add_item(RemoveFromWhitelistButton(member_id, nickname))
            self.add_item(IgnoreLeaveButton(member_id, nickname))


class PersistentViewManager:
    """Менеджер для регистрации и восстановления персистентных View."""
    
    def __init__(self, bot):
        self.bot = bot
        self.registered_views = {}
    
    def register_view(self, view_class, view_id: str = None):
        """Регистрирует персистентное представление."""
        if view_id is None:
            view_id = view_class.__name__
            
        self.registered_views[view_id] = view_class
        logger.info(f"Зарегистрировано персистентное представление: {view_id}")
    
    async def restore_views_from_messages(self):
        """
        Восстанавливает View из существующих сообщений в каналах.
        Вызывается при запуске бота.
        """
        logger.info("Начинаем восстановление персистентных представлений...")
        restored_count = 0
        
        try:
            # Получаем все гильдии бота
            for guild in self.bot.guilds:
                logger.info(f"Обрабатываем сервер: {guild.name}")
                
                # Проходим по всем каналам
                for channel in guild.text_channels:
                    try:
                        # Получаем последние сообщения от бота (увеличиваем лимит для лучшего покрытия)
                        message_count = 0
                        async for message in channel.history(limit=200):
                            message_count += 1
                            if message.author == self.bot.user and message.components:
                                success = await self._restore_view_for_message(message)
                                if success:
                                    restored_count += 1
                                
                    except discord.Forbidden:
                        # Нет доступа к каналу
                        logger.debug(f"Нет доступа к каналу {channel.name}")
                        continue
                    except discord.HTTPException as e:
                        logger.warning(f"HTTP ошибка при обработке канала {channel.name}: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Ошибка при обработке канала {channel.name}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Ошибка при восстановлении представлений: {e}")
        
        logger.info(f"Восстановление завершено. Восстановлено представлений: {restored_count}")
    
    async def _restore_view_for_message(self, message: discord.Message):
        """Восстанавливает View для конкретного сообщения."""
        try:
            # Анализируем кнопки в сообщении
            restored_view = None
            
            for action_row in message.components:
                for component in action_row.children:
                    if hasattr(component, 'custom_id') and component.custom_id:
                        # Пропускаем кнопки с состоянием загрузки или обработанные
                        if (component.custom_id.endswith('_loading') or 
                            component.custom_id.startswith('removed_') or 
                            component.custom_id.startswith('ignored_') or
                            component.custom_id.startswith('candidate_disabled_')):
                            continue
                            
                        restored_view = self._create_view_from_custom_id(component.custom_id, message)
                        if restored_view:
                            break
                if restored_view:
                    break
            
            if restored_view:
                # Добавляем восстановленное представление к боту
                self.bot.add_view(restored_view)
                logger.debug(f"Восстановлено представление для сообщения {message.id} в канале {message.channel.name}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при восстановлении представления для сообщения {message.id}: {e}")
            
        return False
    
    def _create_view_from_custom_id(self, custom_id: str, message: discord.Message):
        """Создает соответствующее View на основе custom_id."""
        try:
            # Определяем тип View по custom_id
            if custom_id.startswith(('approve_', 'reject_', 'candidate_')):
                return self._restore_application_view(message)
            elif custom_id.startswith(('remove_whitelist_', 'ignore_leave_')):
                return self._restore_member_leave_view(message)
                
        except Exception as e:
            logger.error(f"Ошибка при создании View из custom_id {custom_id}: {e}")
            
        return None
    
    def _restore_application_view(self, message: discord.Message):
        """Восстанавливает ApplicationView из сообщения."""
        view = PersistentApplicationView()
        view.clear_items()
        
        # Анализируем существующие кнопки и воссоздаем их
        for action_row in message.components:
            for component in action_row.children:
                if hasattr(component, 'custom_id') and component.custom_id:
                    # Пропускаем системные кнопки (загрузка, обработанные и т.д.)
                    if (component.custom_id.endswith('_loading') or 
                        component.custom_id.startswith('removed_') or 
                        component.custom_id.startswith('ignored_') or
                        component.custom_id.startswith('candidate_disabled_') or
                        component.disabled):
                        continue
                        
                    button = self._create_button_from_custom_id(component.custom_id)
                    if button:
                        view.add_item(button)
                        
        return view if view.children else None
    
    def _restore_member_leave_view(self, message: discord.Message):
        """Восстанавливает MemberLeaveView из сообщения."""
        view = PersistentMemberLeaveView()
        
        # Анализируем существующие кнопки и воссоздаем их
        for action_row in message.components:
            for component in action_row.children:
                if hasattr(component, 'custom_id') and component.custom_id:
                    # Пропускаем системные кнопки (загрузка, обработанные и т.д.)
                    if (component.custom_id.endswith('_loading') or 
                        component.custom_id.startswith('removed_') or 
                        component.custom_id.startswith('ignored_') or
                        component.disabled):
                        continue
                        
                    button = self._create_button_from_custom_id(component.custom_id)
                    if button:
                        view.add_item(button)
                        
        return view if view.children else None
    
    def _create_button_from_custom_id(self, custom_id: str):
        """Создает кнопку из custom_id."""
        try:
            # Пробуем создать каждый тип кнопки
            for button_class in [ApproveButton, RejectButton, CandidateButton, 
                                RemoveFromWhitelistButton, IgnoreLeaveButton]:
                try:
                    button = button_class.from_custom_id(custom_id)
                    if button:
                        return button
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Ошибка при создании кнопки из custom_id {custom_id}: {e}")
            
        return None


# Deprecated - оставляем для совместимости
ApplicationView = PersistentApplicationView
MemberLeaveView = PersistentMemberLeaveView
