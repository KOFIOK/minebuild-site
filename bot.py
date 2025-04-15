import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from mcrcon import MCRcon
import socket
import time
import re

load_dotenv()

class MineBuildBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        
    async def setup_hook(self):
        self.add_view(ApplicationView())  # Добавляем персистентные кнопки
        
    async def on_ready(self):
        print(f'Бот {self.user} запущен!')

class RejectModal(discord.ui.Modal, title="Отказ в заявке"):
    reason = discord.ui.TextInput(
        label="Укажите причину отказа",
        style=discord.TextStyle.paragraph,
        placeholder="Опишите, почему вы отказываете в заявке...",
        required=True,
        max_length=1024
    )

    def __init__(self, discord_id: str, message_url: str):
        super().__init__()
        self.discord_id = discord_id
        self.message_url = message_url

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Получаем пользователя
            member = await interaction.guild.fetch_member(int(self.discord_id))
            if member:
                # Отправляем сообщение пользователю
                try:
                    await member.send(f"# ❌ Вашей заявке было отказано.\n> Причина: {self.reason.value}\n\nВы подавали заявку на сервер **MineBuild**. По всей видимости, она не подходит под наши критерии. Если считаете, что это ошибка, то смело пишите в <#1070354020964769904>.")
                except discord.Forbidden:
                    print(f"Не удалось отправить личное сообщение пользователю {self.discord_id}")

            # Отправляем сообщение в лог-канал
            log_channel = interaction.guild.get_channel(1277415977549566024)
            if log_channel:
                await log_channel.send(
                    f"# Куратор <@{interaction.user.id}> отказал [заявке]({self.message_url}) по причине:\n> {self.reason.value}"
                )

            # Обновляем оригинальное сообщение
            view = discord.ui.View()
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
            await interaction.response.send_message(f"Произошла ошибка: {str(e)}", ephemeral=True)

class RejectButton(discord.ui.Button):
    def __init__(self, discord_id: str):
        super().__init__(
            style=discord.ButtonStyle.red,
            label="Отказать",
            custom_id=f"reject_{discord_id}",
            emoji="❎"
        )
        
    async def callback(self, interaction: discord.Interaction):
        # Проверяем права пользователя (администратор или роль модератора)
        has_permission = (
            interaction.user.guild_permissions.administrator or
            any(role.id == 1277399739561672845 for role in interaction.user.roles)
        )
        
        if not has_permission:
            await interaction.response.send_message(
                "У вас нет прав для отказа заявок. Необходимо быть администратором или модератором.", 
                ephemeral=True
            )
            return

        # Получаем URL сообщения
        message_url = interaction.message.jump_url
        discord_id = self.custom_id.split('_')[1]

        # Показываем модальное окно для ввода причины
        await interaction.response.send_modal(RejectModal(discord_id, message_url))

class ApproveButton(discord.ui.Button):
    def __init__(self, discord_id: str):
        super().__init__(
            style=discord.ButtonStyle.green,
            label="Одобрить",
            custom_id=f"approve_{discord_id}",
            emoji="✅"
        )
        
    async def callback(self, interaction: discord.Interaction):
        # Проверяем права пользователя (администратор или роль модератора)
        has_permission = (
            interaction.user.guild_permissions.administrator or
            any(role.id == 1277399739561672845 for role in interaction.user.roles)
        )
        
        if not has_permission:
            await interaction.response.send_message(
                "У вас нет прав для одобрения заявок. Необходимо быть администратором или модератором.", 
                ephemeral=True
            )
            return

        discord_id = self.custom_id.split('_')[1]
        role = interaction.guild.get_role(1150073275184074803)
        
        if not role:
            await interaction.response.send_message("Роль не найдена.", ephemeral=True)
            return

        try:
            member = await interaction.guild.fetch_member(int(discord_id))
            if not member:
                await interaction.response.send_message("Пользователь не найден.", ephemeral=True)
                return

            # Отправляем сообщение в лог-канал
            log_channel = interaction.guild.get_channel(1277415977549566024)
            if log_channel:
                await log_channel.send(
                    f"## Куратор <@{interaction.user.id}> одобрил [заявку]({interaction.message.jump_url})."
                )

            # Получаем никнейм из заявки
            minecraft_nickname = None
            for embed in interaction.message.embeds:
                for field in embed.fields:
                    if field.name == 'Ваш никнейм в Minecraft':
                        minecraft_nickname = field.value
                        break
                if minecraft_nickname:
                    break

            # Отвечаем на взаимодействие
            await interaction.response.defer(ephemeral=True)

            if minecraft_nickname:
                try:
                    # Пробуем изменить никнейм
                    try:
                        await member.edit(nick=minecraft_nickname)
                    except discord.Forbidden:
                        print(f"Не удалось изменить никнейм пользователю {discord_id}")
                        await interaction.followup.send(
                            "Не удалось изменить никнейм пользователя. Пожалуйста, сделайте это вручную.",
                            ephemeral=True
                        )
                    
                    # Добавляем в белый список через RCON
                    try:
                        # Проверяем доступность сервера
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(5)  # 5 секунд таймаут
                        result = sock.connect_ex((os.getenv('RCON_HOST'), int(os.getenv('RCON_PORT'))))
                        sock.close()
                        
                        if result != 0:
                            print(f"Сервер недоступен. Код ошибки: {result}")
                            await interaction.followup.send(
                                "Сервер Minecraft недоступен. Пожалуйста, проверьте его состояние и добавьте игрока в белый список вручную.",
                                ephemeral=True
                            )
                            return
                        
                        # Пробуем подключиться к RCON
                        with MCRcon(
                            os.getenv('RCON_HOST'),
                            os.getenv('RCON_PASSWORD'),
                            int(os.getenv('RCON_PORT'))
                        ) as mcr:
                            # Даем серверу время на обработку команды
                            time.sleep(1)
                            response = mcr.command(f"uw add {minecraft_nickname}")
                            
                            # Очищаем ответ от форматирования Minecraft
                            clean_response = re.sub(r'§[0-9a-fk-or]', '', response)
                            clean_response = clean_response.strip()
                            
                            print(f"RCON response: {clean_response}")
                            
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
                    except socket.timeout:
                        print("Таймаут при подключении к серверу")
                        await interaction.followup.send(
                            "Таймаут при подключении к серверу. Пожалуйста, попробуйте позже или добавьте игрока вручную.",
                            ephemeral=True
                        )
                    except ConnectionRefusedError:
                        print("Соединение отклонено сервером")
                        await interaction.followup.send(
                            "Соединение отклонено сервером. Пожалуйста, проверьте настройки RCON и добавьте игрока вручную.",
                            ephemeral=True
                        )
                    except Exception as e:
                        print(f"Ошибка RCON: {str(e)}")
                        await interaction.followup.send(
                            f"Произошла ошибка при добавлении в белый список: {str(e)}. Пожалуйста, добавьте игрока вручную.",
                            ephemeral=True
                        )
                except Exception as e:
                    print(f"Ошибка при обработке заявки: {str(e)}")
                    await interaction.followup.send(
                        f"Произошла ошибка при обработке заявки: {str(e)}",
                        ephemeral=True
                    )

            # Добавляем роль
            await member.add_roles(role)
            
            # Создаем новую view с неактивной кнопкой
            view = discord.ui.View()
            button = discord.ui.Button(
                style=discord.ButtonStyle.green,
                label="Одобрено",
                emoji="✅",
                disabled=True,
                custom_id=f"approved_{discord_id}"
            )
            view.add_item(button)
            
            # Обновляем сообщение с новой view и текстом
            await interaction.message.edit(
                content=f"-# Заявка игрока <@{discord_id}> одобрена!",
                view=view
            )
            
            # Отправляем личное сообщение пользователю
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
                print(f"Не удалось отправить личное сообщение пользователю {discord_id}")
            
        except Exception as e:
            await interaction.followup.send(f"Произошла ошибка: {str(e)}", ephemeral=True)

class ApplicationView(discord.ui.View):
    def __init__(self, discord_id: str):
        super().__init__(timeout=None)  # Персистентные кнопки
        self.discord_id = discord_id
        self.add_item(ApproveButton(discord_id))
        self.add_item(RejectButton(discord_id)) 

async def create_application_message(channel, discord_id: str, embed: discord.Embed) -> bool:
    """Создает сообщение с заявкой в указанном канале"""
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
        
        view = ApplicationView()
        view.add_item(ApproveButton(discord_id))
        view.add_item(RejectButton(discord_id))
        
        await channel.send(
            content=f"-# ||<@&1277399739561672845>||\n## <@{discord_id}> отправил заявку на сервер!",
            embeds=embeds,
            view=view
        )
        return True
    except Exception as e:
        print(f"Ошибка при отправке заявки: {str(e)}")
        return False

bot = MineBuildBot()

if __name__ == '__main__':
    bot.run(os.getenv('DISCORD_BOT_TOKEN')) 