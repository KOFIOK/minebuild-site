"""
Базовый класс для кнопок Discord UI в боте MineBuild
"""

import logging
import discord
from typing import Optional

logger = logging.getLogger("MineBuildBot.UI")


class BaseActionButton(discord.ui.Button):
    """Базовый класс для кнопок действий с защитой от случайных множественных нажатий."""
    
    def __init__(self, style, label, custom_id, emoji=None, disabled=False):
        super().__init__(
            style=style,
            label=label,
            custom_id=custom_id,
            emoji=emoji,
            disabled=disabled
        )
        
    @classmethod
    def from_custom_id(cls, custom_id: str):
        """
        Создает кнопку из custom_id для восстановления после рестарта.
        Переопределяется в дочерних классах.
        """
        raise NotImplementedError("Subclasses must implement from_custom_id")
        
    async def callback(self, interaction: discord.Interaction) -> None:
        """Базовый обработчик нажатия с защитой от повторных нажатий."""
        # Немедленно блокируем все кнопки в сообщении, чтобы избежать повторных нажатий
        try:
            # Создаем копию текущего view с неактивными кнопками
            view = discord.ui.View(timeout=None)
            
            # Добавляем копию этой кнопки с индикатором загрузки
            loading_button = discord.ui.Button(
                style=self.style,
                label="Обработка...",
                emoji="⌛",
                disabled=True,
                custom_id=f"{self.custom_id}_loading"
            )
            view.add_item(loading_button)
            
            # Сохраняем ссылку на оригинальное сообщение
            original_message = interaction.message
            
            # Обновляем сообщение, заменяя все кнопки на неактивные
            await interaction.message.edit(view=view)
            
            # Вызываем основной обработчик действия
            await self.process_action(interaction, original_message)
                
        except Exception as e:
            logger.error(f"Ошибка при обработке нажатия кнопки: {e}", exc_info=True)
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
        """
        Основная логика обработки действия кнопки.
        Переопределяется в дочерних классах.
        
        Args:
            interaction: Взаимодействие Discord
            original_message: Оригинальное сообщение с кнопками
        """
        pass
