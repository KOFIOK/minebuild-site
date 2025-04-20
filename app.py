from quart import Quart, render_template, request, jsonify
import discord
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Quart(__name__)

# Максимальное количество символов в одном поле embed
MAX_FIELD_LENGTH = 1024

# Конфигурация вопросов
formQuestions = [
    {
        'id': 'discord',
        'question': 'Ваш Discord ID пользователя',
        'type': 'number',
        'required': True
    },
    {
        'id': 'nickname',
        'question': 'Ваш никнейм в Minecraft',
        'type': 'text',
        'required': True
    },
    {
        'id': 'age',
        'question': 'Ваш возраст',
        'type': 'number',
        'required': True
    },
    {
        'id': 'experience',
        'question': 'Опыт игры в Minecraft',
        'type': 'radio',
        'required': True
    },
    {
        'id': 'gameplay',
        'question': 'Опишите ваш стиль игры',
        'type': 'text',
        'required': True
    },
    {
        'id': 'important',
        'question': 'Что для вас самое важное на приватных серверах?',
        'type': 'text',
        'required': True
    },
    {
        'id': 'about',
        'question': 'Расскажите о себе',
        'type': 'textarea',
        'required': True
    },
    {
        'id': 'biography',
        'question': 'Напишите краткую биографию',
        'type': 'textarea',
        'required': True
    }
]

def split_long_text(text, max_length):
    """Разделяет длинный текст на части с учетом переносов строк и слов"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    words = text.split()
    
    for word in words:
        if len(current_part) + len(word) + 1 <= max_length:
            current_part += (" " + word if current_part else word)
        else:
            parts.append(current_part)
            current_part = word
    
    if current_part:
        parts.append(current_part)
    
    return parts

@app.route('/')
async def index():
    return await render_template('index.html')

@app.route('/about')
async def about():
    return await render_template('about.html')

@app.route('/rules')
async def rules():
    return await render_template('rules.html')

@app.route('/build')
async def build():
    return await render_template('build.html')

@app.route('/apply')
async def apply():
    return await render_template('apply.html')

@app.route('/api/submit-application', methods=['POST'])
async def submit_application():
    try:
        print("Получен запрос на отправку заявки")
        data = await request.get_json()
        print("Полученные данные:", data)
        
        if not data:
            print("Ошибка: данные не получены")
            return jsonify({"status": "error", "message": "Данные не получены"}), 400

        # Проверяем обязательные поля
        required_fields = ['discord', 'nickname', 'age', 'experience', 'about', 'biography']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            print(f"Ошибка: отсутствуют поля {missing_fields}")
            return jsonify({
                "status": "error",
                "message": f"Не заполнены обязательные поля: {', '.join(missing_fields)}"
            }), 400

        # Проверяем, существует ли пользователь с указанным Discord ID
        discord_id = str(data['discord'])
        try:
            user = await app.bot.fetch_user(discord_id)
        except discord.NotFound:
            return jsonify({
                "status": "error",
                "message": "Пользователь с указанным Discord ID не найден."
            }), 400

        # Получаем все гильдии, в которых находится бот
        guilds = app.bot.guilds
        member = None

        # Проверяем, является ли пользователь участником хотя бы одной из гильдий
        for guild in guilds:
            try:
                member = await guild.fetch_member(user.id)
                break  # Если нашли участника, выходим из цикла
            except discord.NotFound:
                continue  # Если участник не найден, продолжаем проверку

        if member is None:
            return jsonify({
                "status": "error",
                "message": "Вы должны быть участником дискорд-сервера для подачи заявки."
            }), 403

        # Создаем embed сообщение
        embed = discord.Embed(
            title="📝 Новая заявка на сервер",
            color=0x00E5A1,
            timestamp=datetime.now()
        )
        
        # Добавляем поля с проверкой длины
        for field in formQuestions:
            value = str(data.get(field['id'], 'Не указано'))
            if len(value) > MAX_FIELD_LENGTH:
                parts = split_long_text(value, MAX_FIELD_LENGTH)
                for i, part in enumerate(parts, 1):
                    embed.add_field(
                        name=f"{field['question']} (часть {i}/{len(parts)})",
                        value=part,
                        inline=False
                    )
            else:
                embed.add_field(
                    name=field['question'],
                    value=value,
                    inline=False
                )

        # Получаем канал
        channel_id = 1360709668770418789
        channel = app.bot.get_channel(channel_id)
        
        if not channel:
            print(f"Ошибка: канал {channel_id} не найден")
            return jsonify({
                "status": "error",
                "message": "Канал для отправки заявок недоступен"
            }), 500

        # Отправляем сообщение используя функцию из bot.py
        from bot import create_application_message
        success = await create_application_message(channel, discord_id, embed)
        
        if not success:
            return jsonify({
                "status": "error",
                "message": "Не удалось отправить заявку в Discord"
            }), 500

        print("Заявка успешно отправлена")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"Критическая ошибка при отправке заявки: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Внутренняя ошибка сервера: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(debug=True)