"""
Команды для Discord бота MineBuild
"""

import logging
import discord
from discord.ext import commands
from typing import Union

from ..config import (
    MODERATOR_ROLE_ID,
    WHITELIST_ROLE_ID,
    CANDIDATE_ROLE_ID,
    LOG_CHANNEL_ID
)
from ..utils.helpers import has_moderation_permissions, send_welcome_message
from ..utils.minecraft import add_to_whitelist_wrapper

logger = logging.getLogger("MineBuildBot.Commands")


class AdminCommands(commands.Cog):
    """Административные команды для бота."""
    
    def __init__(self, bot):
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


async def setup(bot):
    """Функция для подключения cog'а к боту."""
    await bot.add_cog(AdminCommands(bot))
