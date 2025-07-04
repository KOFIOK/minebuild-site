"""
Команды для Discord бота MineBuild
"""

import logging
import discord
from discord.ext import commands
from typing import Union

from ..config_manager import (
    get_moderator_role_id,
    get_whitelist_role_id,
    get_candidate_role_id,
    get_log_channel_id,
    get_minecraft_commands
)
from ..utils.helpers import has_moderation_permissions, send_welcome_message
from ..utils.minecraft import add_to_whitelist_wrapper, remove_from_whitelist, get_whitelist

logger = logging.getLogger("MineBuildBot.Commands")


class AdminCommands(commands.Cog):
    """Административные команды для бота."""
    
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="whitelist-add",
        description="Добавить игрока в whitelist (выдать роль, добавить в Minecraft whitelist)"
    )
    @discord.app_commands.describe(
        user="Пользователь Discord, которого нужно добавить",
        nickname="Никнейм игрока в Minecraft"
    )
    async def whitelist_add(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        nickname: str
    ):
        """Добавляет игрока в whitelist."""
        # Проверяем права модератора
        if not has_moderation_permissions(interaction.user):
            await interaction.response.send_message(
                "У вас нет прав для управления whitelist. Необходимо быть администратором или модератором.",
                ephemeral=True
            )
            return

        # Валидация никнейма Minecraft
        if not nickname or len(nickname) < 3 or len(nickname) > 16:
            await interaction.response.send_message(
                "Никнейм Minecraft должен содержать от 3 до 16 символов.",
                ephemeral=True
            )
            return
        
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', nickname):
            await interaction.response.send_message(
                "Никнейм Minecraft может содержать только буквы, цифры и символ подчеркивания.",
                ephemeral=True
            )
            return

        try:
            await interaction.response.defer(ephemeral=True)

            # Проверяем наличие роли whitelist
            whitelist_role = interaction.guild.get_role(get_whitelist_role_id())
            if not whitelist_role:
                await interaction.followup.send(
                    "Роль для whitelist не найдена.",
                    ephemeral=True
                )
                return

            # Если у пользователя есть роль кандидата, снимаем её
            candidate_role = interaction.guild.get_role(get_candidate_role_id())
            if candidate_role and candidate_role in user.roles:
                await user.remove_roles(candidate_role)
                logger.info(f"Снята роль кандидата с пользователя {user.id}")

            # Добавляем роль whitelist
            await user.add_roles(whitelist_role)
            
            # Пробуем изменить никнейм
            try:
                await user.edit(nick=nickname)
            except discord.Forbidden:
                logger.warning(f"Не удалось изменить никнейм пользователю {user.id}")
                await interaction.followup.send(
                    "Не удалось изменить никнейм пользователя. Пожалуйста, сделайте это вручную.",
                    ephemeral=True
                )
            
            # Добавляем в Minecraft whitelist
            await add_to_whitelist_wrapper(interaction.followup, nickname)
            
            # Отправляем приветственное сообщение
            await send_welcome_message(user)

            # Логируем в канал
            log_channel = interaction.guild.get_channel(get_log_channel_id())
            if log_channel:
                await log_channel.send(
                    f"## <@{interaction.user.id}> добавил <@{user.id}> (`{nickname}`) в whitelist"
                )

            # Успешное добавление
            await interaction.followup.send(
                f"✅ Игрок <@{user.id}> (`{nickname}`) успешно добавлен в whitelist!",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Ошибка в whitelist add: {e}", exc_info=True)
            await interaction.followup.send(
                f"Произошла ошибка при добавлении игрока: {str(e)}",
                ephemeral=True
            )

    @discord.app_commands.command(
        name="whitelist-remove",
        description="Удалить игрока из whitelist (убрать роль, удалить из Minecraft whitelist)"
    )
    @discord.app_commands.describe(
        user="Пользователь Discord, которого нужно удалить",
        nickname="Никнейм игрока в Minecraft"
    )
    async def whitelist_remove(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        nickname: str
    ):
        """Удаляет игрока из whitelist."""
        # Проверяем права модератора
        if not has_moderation_permissions(interaction.user):
            await interaction.response.send_message(
                "У вас нет прав для управления whitelist. Необходимо быть администратором или модератором.",
                ephemeral=True
            )
            return

        # Валидация никнейма Minecraft
        if not nickname or len(nickname) < 3 or len(nickname) > 16:
            await interaction.response.send_message(
                "Никнейм Minecraft должен содержать от 3 до 16 символов.",
                ephemeral=True
            )
            return
        
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', nickname):
            await interaction.response.send_message(
                "Никнейм Minecraft может содержать только буквы, цифры и символ подчеркивания.",
                ephemeral=True
            )
            return

        try:
            await interaction.response.defer(ephemeral=True)

            # Проверяем наличие роли whitelist
            whitelist_role = interaction.guild.get_role(get_whitelist_role_id())
            if not whitelist_role:
                await interaction.followup.send(
                    "Роль для whitelist не найдена.",
                    ephemeral=True
                )
                return

            # Убираем роль whitelist
            if whitelist_role in user.roles:
                await user.remove_roles(whitelist_role)
            
            # Удаляем из Minecraft whitelist
            success = await remove_from_whitelist(nickname)
            
            if success:
                # Логируем в канал
                log_channel = interaction.guild.get_channel(get_log_channel_id())
                if log_channel:
                    await log_channel.send(
                        f"## <@{interaction.user.id}> удалил <@{user.id}> (`{nickname}`) из whitelist"
                    )

                await interaction.followup.send(
                    f"✅ Игрок <@{user.id}> (`{nickname}`) успешно удален из whitelist!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"⚠️ Роль удалена, но произошла ошибка при удалении `{nickname}` из Minecraft whitelist. Проверьте сервер.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Ошибка в whitelist remove: {e}", exc_info=True)
            await interaction.followup.send(
                f"Произошла ошибка при удалении игрока: {str(e)}",
                ephemeral=True
            )

    @discord.app_commands.command(
        name="whitelist-list",
        description="Показать список игроков в whitelist"
    )
    async def whitelist_list(self, interaction: discord.Interaction):
        """Показывает список игроков в whitelist."""
        try:
            await interaction.response.defer(ephemeral=True)

            # Получаем список из Minecraft
            minecraft_whitelist = await get_whitelist()
            
            if not minecraft_whitelist:
                await interaction.followup.send(
                    "📋 **Whitelist пуст**\n\nВ whitelist сервера нет ни одного игрока.",
                    ephemeral=True
                )
                return

            # Форматируем список в красивом виде
            players_text = "\n".join([f"• `{player}`" for player in sorted(minecraft_whitelist)])
            
            embed = discord.Embed(
                title="📋 Список игроков в Whitelist",
                description=f"**Всего игроков:** {len(minecraft_whitelist)}\n\n{players_text}",
                color=0x00E5A1  # Зеленый цвет
            )
            embed.set_footer(text="Данные получены с сервера Minecraft")
            
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Ошибка в whitelist list: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    f"Произошла ошибка при получении списка whitelist: {str(e)}",
                    ephemeral=True
                )
            except Exception as followup_error:
                logger.error(f"Ошибка при отправке followup сообщения: {followup_error}", exc_info=True)


async def setup(bot):
    """Функция для подключения cog'а к боту."""
    await bot.add_cog(AdminCommands(bot))
