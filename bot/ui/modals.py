"""
Модальные окна для Discord UI в боте MineBuild
"""

import logging
import discord

from ..config import CANDIDATE_ROLE_ID, LOG_CHANNEL_ID
from ..utils.api import clear_web_application_status

logger = logging.getLogger("MineBuildBot.UI.Modals")


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
            # Сначала отвечаем на взаимодействие, чтобы предотвратить ошибку "Interaction already responded to"
            await interaction.response.defer(ephemeral=True)
            
            # ТЕПЕРЬ блокируем кнопки, показывая что идет обработка
            loading_view = discord.ui.View(timeout=None)
            loading_button = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label="Обработка отказа...",
                emoji="⌛",
                disabled=True,
                custom_id=f"reject_processing_{self.discord_id}"
            )
            loading_view.add_item(loading_button)
            
            # Обновляем сообщение с индикатором загрузки
            await interaction.message.edit(view=loading_view)
            
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
            
            # Очищаем статус на веб-сайте - пользователь сможет подать заявку заново
            await clear_web_application_status(self.discord_id)
            
            # Используем followup вместо response, так как мы уже ответили на взаимодействие
            await interaction.followup.send("Отказ в заявке успешно обработан.", ephemeral=True)

        except Exception as e:
            logger.error(f"Ошибка при обработке отказа: {e}", exc_info=True)
            # Если возникла ошибка и мы еще не ответили на взаимодействие
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Произошла ошибка: {str(e)}", ephemeral=True)
            else:
                # Используем followup, если уже ответили
                await interaction.followup.send(f"Произошла ошибка: {str(e)}", ephemeral=True)
