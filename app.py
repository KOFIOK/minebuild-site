from flask import Flask, render_template, request, jsonify, redirect, url_for, session, make_response, current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import requests
import json
import logging
import hashlib
import time
import uuid
from datetime import datetime, timedelta
import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Импорт модуля аутентификации
from auth import DiscordAuth, require_auth, require_guild_member, can_submit_application

app = Flask(__name__)

# Генерируем надежный SECRET_KEY
# Используем из переменной окружения или генерируем только один раз
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    import secrets
    SECRET_KEY = secrets.token_hex(32)
    print(f"⚠️ ВНИМАНИЕ: SECRET_KEY не задан в .env, используется случайный: {SECRET_KEY}")
    print("⚠️ Добавьте SECRET_KEY в файл .env для стабильной работы сессий!")

app.config['SECRET_KEY'] = SECRET_KEY

# Настройки сессий для разработки (для продакшена нужно изменить)
app.config.update({
    'SESSION_COOKIE_SECURE': False,  # True только для HTTPS
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'PERMANENT_SESSION_LIFETIME': 86400 * 30  # 30 дней в секундах
})

# Настройки Discord OAuth
app.config.update({
    'DISCORD_CLIENT_ID': os.environ.get('DISCORD_CLIENT_ID'),
    'DISCORD_CLIENT_SECRET': os.environ.get('DISCORD_CLIENT_SECRET'),
    'DISCORD_REDIRECT_URI': os.environ.get('DISCORD_REDIRECT_URI', 'http://127.0.0.1:5000/auth/discord/callback'),
    'DISCORD_GUILD_ID': os.environ.get('DISCORD_GUILD_ID'),
})

# Проверяем, что все необходимые переменные загружены (только в production)
# В тестовом окружении пропускаем эту проверку
is_testing = os.environ.get('TESTING') == 'true' or 'pytest' in sys.modules
if not is_testing:
    required_env_vars = ['DISCORD_CLIENT_ID', 'DISCORD_CLIENT_SECRET', 'DISCORD_GUILD_ID']
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    if missing_vars:
        print(f"❌ ОШИБКА: Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        print("Пожалуйста, настройте файл .env согласно инструкции в DISCORD_OAUTH_SETUP.md")
    else:
        print(f"✅ Discord OAuth настроен:")
        print(f"   Client ID: {os.environ.get('DISCORD_CLIENT_ID')}")
        print(f"   Guild ID: {os.environ.get('DISCORD_GUILD_ID')}")
        print(f"   Redirect URI: {os.environ.get('DISCORD_REDIRECT_URI', 'http://127.0.0.1:5000/auth/discord/callback')}")
else:
    print("🧪 Тестовое окружение: пропускаем проверку переменных окружения")

# Инициализация Discord Auth
discord_auth = DiscordAuth()
discord_auth.init_app(app)
app.discord_auth = discord_auth

# Глобальная переменная для управления статусом приема заявок
# Чтобы закрыть прием заявок - установите значение False
# Чтобы открыть прием заявок - установите значение True
APPLICATIONS_OPEN = True

# Настройка логгера
# Создаем форматтер для логов
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Создаем хэндлер для файла
file_handler = logging.FileHandler('main.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Создаем хэндлер для консоли
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)  # INFO для консоли чтобы не было слишком много вывода
console_handler.setFormatter(formatter)

# Настраиваем корневой логгер
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)  # Общий уровень - DEBUG
root_logger.handlers = []  # Очищаем существующие хэндлеры
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Получаем логгер для приложения
logger = logging.getLogger(__name__)
logger.info("Логирование настроено - запись в файл и консоль")

# Добавляем Jinja2 фильтры
@app.template_filter('format_datetime')
def format_datetime_filter(dt):
    """Форматирует datetime объект в читаемый формат."""
    if dt is None:
        return 'Неизвестно'
    
    if isinstance(dt, str):
        try:
            # Пытаемся распарсить строку как ISO формат
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return dt  # Возвращаем как есть, если не удалось распарсить
    
    if isinstance(dt, datetime):
        # Форматируем в удобочитаемый вид
        return dt.strftime('%d.%m.%Y в %H:%M')
    
    return str(dt)

# Конфигурация ЮMoney API
YOOMONEY_CLIENT_ID = "F5301946C2DEFAA64BB2BE12EBDC4D7A0074754D58364B7E0A84BE12D5542134"
YOOMONEY_REDIRECT_URI = "http://minebuild.fun"
YOOMONEY_NOTIFICATION_URI = "https://minebuild.fun/yoomoney-notification"
YOOMONEY_SECRET_KEY = os.environ.get('YOOMONEY_SECRET_KEY', '') # Секретный ключ для проверки подписи уведомлений
SUCCESS_URL = "https://minebuild.fun/donation-success"  # URL для редиректа после успешной оплаты
FAIL_URL = "https://minebuild.fun/donation-fail"        # URL для редиректа при ошибке

# Главные страницы
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/rules')
def rules():
    return render_template('rules.html')

@app.route('/build')
def build():
    return render_template('build.html')

@app.route('/apply')
@require_auth
@require_guild_member
@can_submit_application
def apply():
    """Страница подачи заявки (требует авторизации)"""
    current_user = discord_auth.get_current_user()
    return render_template('apply.html', 
                         applications_open=APPLICATIONS_OPEN,
                         current_user=current_user)

@app.route('/donate')
def donate():
    return render_template('donate.html')

# API для обработки платежей
@app.route('/api/create-payment', methods=['POST'])
def create_payment():
    try:
        # Логируем данные запроса для отладки
        logger.info(f"Получен запрос на создание платежа")
        
        # Проверяем, есть ли данные запроса
        if not request.is_json:
            logger.error("Запрос не содержит JSON данных")
            return jsonify({'success': False, 'error': 'Ожидаются данные в формате JSON'}), 400
            
        data = request.json
        logger.debug(f"Получены данные из формы: {data}")
        
        # Валидация данных
        if not data or 'amount' not in data or 'comment' not in data:
            logger.error("Неверные параметры запроса: отсутствуют обязательные поля")
            return jsonify({'success': False, 'error': 'Неверные параметры запроса'}), 400
        
        amount = float(data['amount'])
        nickname = data['comment']  # Получаем ник из поля comment
        payment_type = data.get('payment_type', 'AC')  # По умолчанию - банковская карта
        
        if amount < 100:
            logger.warning(f"Попытка создать платеж на сумму меньше минимальной: {amount}")
            return jsonify({'success': False, 'error': 'Минимальная сумма - 100 ₽'}), 400
        
        # Создаем уникальный идентификатор для платежа
        payment_id = str(uuid.uuid4())
        
        # Создаем защищенный токен для доната
        donation_token = create_donation_token(nickname, amount, payment_id)
        
        # Формируем параметры для формы ЮMoney
        quickpay_form = {
            "receiver": "4100116641745516",  # Номер кошелька ЮMoney для приема платежей
            "quickpay-form": "donate",
            "targets": f"Поддержка MineBuild от игрока {nickname}",
            "paymentType": payment_type,
            "sum": amount,
            "formcomment": f"Поддержка MineBuild от игрока {nickname}",
            "short-dest": f"Поддержка MineBuild от игрока {nickname}",
            "label": payment_id,
            "comment": nickname,
            # Добавляем токен в successURL для проверки подлинности
            "successURL": f"{SUCCESS_URL}?token={donation_token}",
            "need-fio": "false",
            "need-email": "false",
            "need-phone": "false",
            "need-address": "false"
        }
        
        # Формируем URL для редиректа на форму ЮMoney
        quickpay_url = "https://yoomoney.ru/quickpay/confirm.xml"
        
        # Создаем параметры URL
        query_string = "&".join([f"{k}={requests.utils.quote(str(v))}" for k, v in quickpay_form.items()])
        redirect_url = f"{quickpay_url}?{query_string}"
        
        # В реальном приложении здесь можно сохранить информацию о платеже в базу данных
        logger.info(f"Создан платеж: ID={payment_id}, Игрок={nickname}, Сумма={amount}, Токен создан")
        logger.debug(f"Redirect URL: {redirect_url}")
        
        # Возвращаем данные для формирования URL на фронтенде
        return jsonify({
            'success': True,
            'payment_id': payment_id,
            'donation_token': donation_token,  # Передаем токен клиенту
            'redirect_url': redirect_url
        })
            
    except Exception as e:
        logger.exception(f"Ошибка при обработке платежа: {str(e)}")
        return jsonify({'success': False, 'error': 'Произошла ошибка при обработке запроса'}), 500

# API для проверки статуса платежа
@app.route('/api/check-payment/<payment_id>', methods=['GET'])
def check_payment(payment_id):
    # В текущей реализации с формой ЮMoney мы не можем проверять статус программно
    # Для этого нужно настраивать уведомления от ЮMoney
    # Возвращаем статус pending, чтобы пользователь перешел на сайт оплаты
    
    logger.info(f"Запрос на проверку статуса платежа: {payment_id}")
    return jsonify({
        'success': True,
        'status': 'pending',
        'message': 'Пожалуйста, завершите платеж на сайте ЮMoney'
    })

# Страницы успешного платежа и ошибки
@app.route('/donation-success')
def donation_success():
    try:
        # Проверяем токен безопасности (если он есть)
        token = request.args.get('token')
        token_data = None
        is_token_valid = False
        
        if token:
            # Верифицируем токен
            token_data = verify_donation_token(token)
            is_token_valid = token_data is not None
            
            if is_token_valid:
                # Используем данные из токена
                nickname = token_data.get('nickname')
                amount = token_data.get('amount')
                payment_id = token_data.get('payment_id')
                logger.info(f"Успешная верификация токена доната: игрок={nickname}, сумма={amount}, ID={payment_id}")
            else:
                logger.warning(f"Получен недействительный токен доната: {token}")
        
        # Если нет токена или токен недействителен, используем параметры из URL (менее безопасный метод)
        if not is_token_valid:
            # Получаем параметры из URL после оплаты ЮMoney
            label = request.args.get('label', '')
            amount = request.args.get('sum', 0)
            nickname = request.args.get('comment', '')
            logger.info(f"Использование параметров из URL (без токена): label={label}, сумма={amount}, игрок={nickname}")
            
            # Проверяем наличие данных в параметрах
            if not amount or float(amount) <= 0:
                logger.warning(f"Пустая или нулевая сумма доната: {amount}")
                # Пытаемся получить параметры из запроса cookies
                amount = request.cookies.get('donation_amount', 0)
                nickname = request.cookies.get('donation_nickname', '')
        
        # Проверяем, был ли запрос отправлен AJAX-ом для восстановления параметров
        is_ajax_request = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Логируем информацию о платеже
        logger.info(f"Обработка страницы успешного платежа: игрок={nickname}, сумма={amount}, токен={is_token_valid}")
        
        # Проверка на уже обработанный донат
        donation_processed = request.args.get('processed', 'false') == 'true'
        
        # Обрабатываем донат только если:
        # 1. Либо токен действителен
        # 2. Либо мы получаем уведомление от вебхука ЮMoney (вебхук обрабатывается отдельно)
        # 3. И донат еще не был обработан
        # 4. И это не AJAX-запрос для восстановления данных
        if not is_ajax_request and not donation_processed and nickname and float(amount) > 0:
            if is_token_valid:
                # Если токен действителен - обрабатываем донат
                process_donation_in_discord(nickname, float(amount))
                logger.info(f"Обработан донат через токен: игрок={nickname}, сумма={amount}")
                
                # Помечаем донат как обработанный
                if '?' in request.url:
                    redirect_url = f"{request.url}&processed=true"
                else:
                    redirect_url = f"{request.url}?processed=true"
                return redirect(redirect_url)
            else:
                # Если токен недействителен - логируем это, но не обрабатываем донат
                # Этот сценарий подходит только для обратной совместимости или тестирования
                # В реальной системе донаты без токена не должны обрабатываться здесь,
                # а только через вебхуки ЮMoney
                logger.warning(f"Попытка обработки доната без действительного токена: игрок={nickname}, сумма={amount}")
        
        # Импортируем datetime для шаблона
        from datetime import datetime
        
        # Создаем ответ с рендером шаблона
        response = make_response(render_template('donation_success.html', 
                              nickname=nickname,
                              amount=amount,
                              now=datetime.now,  # Передаем функцию now
                              is_verified=is_token_valid))  # Передаем статус верификации
        
        # Очищаем cookie, если донат был успешно обработан
        if donation_processed or is_token_valid:
            response.delete_cookie('donation_nickname')
            response.delete_cookie('donation_amount')
            
        return response
    except Exception as e:
        logger.exception(f"Ошибка при обработке успешного платежа: {str(e)}")
        from datetime import datetime
        return render_template('donation_success.html', now=datetime.now)

@app.route('/donation-fail')
def donation_fail():
    label = request.args.get('label', '')
    logger.info(f"Неуспешный платеж, label: {label}")
    return render_template('donation_fail.html')

# API для обработки заявок
@app.route('/api/submit-application', methods=['POST'])
@require_auth
@require_guild_member
@can_submit_application
def submit_application():
    try:
        logger.info(f"Получен запрос на отправку заявки")
        
        # Получаем данные авторизованного пользователя
        current_user = discord_auth.get_current_user()
        if not current_user:
            return jsonify({'success': False, 'error': 'Пользователь не авторизован'}), 401
        
        # Проверяем, есть ли данные запроса
        if not request.is_json:
            logger.error("Запрос не содержит JSON данных")
            return jsonify({'success': False, 'error': 'Ожидаются данные в формате JSON'}), 400
            
        data = request.json
        logger.debug(f"Получены данные заявки: {data}")
        
        # Проверка наличия всех необходимых полей
        # Поля соответствуют новой форме заявки
        required_fields = ['nickname', 'name', 'age', 'experience', 'gameplay', 'important', 'about']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.error(f"Неверные параметры запроса: отсутствуют обязательные поля {', '.join(missing_fields)}")
            return jsonify({'success': False, 'error': 'Неверные параметры запроса'}), 400
        
        # Добавляем Discord данные из сессии к данным заявки
        processed_data = data.copy()
        processed_data.update({
            'discord_id': current_user['user_id'],
            'discord_username': current_user['username'],
            'discord_avatar': current_user['avatar_url']
        })
        
        # Отправляем заявку в Discord через бота
        success = process_application_in_discord(processed_data)
        
        if success:
            # Обновляем статус заявки в сессии
            discord_auth.update_application_status('pending')
            
            # Сохраняем статус в файл статусов - это теперь источник истины
            save_application_status(current_user['user_id'], 'pending')
            
            logger.info(f"Заявка успешно отправлена в Discord для пользователя {data.get('name')} (Discord: {current_user['username']})")
            return jsonify({'success': True, 'message': 'Заявка успешно отправлена'})
        else:
            logger.error(f"Ошибка при отправке заявки в Discord для пользователя {data.get('name')}")
            return jsonify({'success': False, 'error': 'Произошла ошибка при отправке заявки'}), 500
            
    except Exception as e:
        logger.exception(f"Ошибка при обработке заявки: {str(e)}")
        return jsonify({'success': False, 'error': 'Произошла ошибка при обработке запроса'}), 500

# API endpoint для обновления статуса заявки из Discord-бота
@app.route('/api/update-application-status', methods=['POST'])
def update_application_status_api():
    """API для обновления статуса заявки из Discord-бота"""
    try:
        # Проверяем API ключ для безопасности
        api_key = request.headers.get('X-API-Key')
        expected_api_key = os.getenv('INTERNAL_API_KEY', 'your-secret-api-key')
        
        if api_key != expected_api_key:
            logger.warning(f"Неверный API ключ при обновлении статуса заявки: {api_key}")
            return jsonify({'error': 'Unauthorized'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        discord_id = data.get('discord_id')
        status = data.get('status')  # 'approved', 'rejected', 'candidate'
        reason = data.get('reason', '')  # Причина отказа (если есть)
        
        if not discord_id or not status:
            return jsonify({'error': 'discord_id and status are required'}), 400
            
        if status not in ['approved', 'rejected', 'candidate']:
            return jsonify({'error': 'Invalid status'}), 400
        
        # Сохраняем статус заявки в файл/базу данных
        # Для простоты используем JSON файл
        status_file_path = os.path.join(os.path.dirname(__file__), 'application_statuses.json')
        
        # Загружаем существующие статусы
        statuses = {}
        if os.path.exists(status_file_path):
            try:
                with open(status_file_path, 'r', encoding='utf-8') as f:
                    statuses = json.load(f)
            except Exception as e:
                logger.error(f"Ошибка при загрузке статусов заявок: {e}")
        
        # Обновляем статус
        statuses[discord_id] = {
            'status': status,
            'timestamp': time.time(),
            'reason': reason
        }
        
        # Сохраняем обновленные статусы
        try:
            with open(status_file_path, 'w', encoding='utf-8') as f:
                json.dump(statuses, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Обновлен статус заявки для Discord ID {discord_id}: {status}")
            return jsonify({'success': True, 'message': 'Status updated successfully'})
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении статуса заявки: {e}")
            return jsonify({'error': 'Failed to save status'}), 500
            
    except Exception as e:
        logger.error(f"Ошибка в API обновления статуса заявки: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# API endpoint для очистки статуса заявки (позволяет подать заявку заново)
@app.route('/api/clear-application-status', methods=['POST'])
def clear_application_status_api():
    """API для очистки статуса заявки из Discord-бота"""
    try:
        # Проверяем API ключ для безопасности
        api_key = request.headers.get('X-API-Key')
        expected_api_key = os.getenv('INTERNAL_API_KEY', 'your-secret-api-key')
        
        if api_key != expected_api_key:
            logger.warning(f"Неверный API ключ при очистке статуса заявки: {api_key}")
            return jsonify({'error': 'Unauthorized'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        discord_id = data.get('discord_id')
        
        if not discord_id:
            return jsonify({'error': 'discord_id is required'}), 400
        
        # Удаляем статус заявки из файла
        status_file_path = os.path.join(os.path.dirname(__file__), 'application_statuses.json')
        
        statuses = {}
        if os.path.exists(status_file_path):
            try:
                with open(status_file_path, 'r', encoding='utf-8') as f:
                    statuses = json.load(f)
            except Exception as e:
                logger.error(f"Ошибка при загрузке статусов заявок: {e}")
        
        # Удаляем статус для данного пользователя
        if str(discord_id) in statuses:
            del statuses[str(discord_id)]
            
            # Сохраняем обновленные статусы
            try:
                with open(status_file_path, 'w', encoding='utf-8') as f:
                    json.dump(statuses, f, ensure_ascii=False, indent=2)
                    
                logger.info(f"Очищен статус заявки для Discord ID {discord_id}")
                return jsonify({'success': True, 'message': 'Status cleared successfully'})
                
            except Exception as e:
                logger.error(f"Ошибка при сохранении статусов заявок: {e}")
                return jsonify({'error': 'Failed to save status'}), 500
        else:
            # Статус уже отсутствует
            return jsonify({'success': True, 'message': 'Status already cleared'})
            
    except Exception as e:
        logger.error(f"Ошибка в API очистки статуса заявки: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Функция для передачи заявки боту Discord
def process_application_in_discord(application_data):
    """
    Асинхронно вызывает обработку заявки в Discord боте
    
    Args:
        application_data: Данные заявки
        
    Returns:
        bool: True если заявка успешно отправлена, иначе False
    """
    try:
        logger.info(f"Обработка заявки для пользователя {application_data.get('name')}")
        logger.debug(f"Данные заявки: {application_data}")
        
        # Проверяем, есть ли доступ к экземпляру бота
        if hasattr(app, 'bot') and app.bot is not None:
            import asyncio
            
            # Получаем ID канала для заявок и создаем embed-сообщение
            import discord
            from bot.config import QUESTION_MAPPING
            
            # Создаем embed-сообщение
            embed = discord.Embed(
                title="Заявка на сервер",
                color=0x00E5A1,
                timestamp=discord.utils.utcnow()
            )
            
            # Обновленный порядок полей согласно новой форме
            field_order = [
                ('nickname', 'Игровой никнейм в Minecraft', True),
                ('name', 'Имя (реальное)', True),
                ('age', 'Возраст', True), 
                ('experience', 'Опыт игры в Minecraft', True),
                ('gameplay', 'Стиль игры', False),
                ('important', 'Что самое важное в приватках?', False),
                ('about', 'Расскажите о себе', False)
            ]
            
            # Добавляем поля в правильном порядке
            for field_id, field_name, is_inline in field_order:
                if field_id in application_data:
                    embed.add_field(
                        name=field_name,
                        value=application_data[field_id],
                        inline=is_inline
                    )
            
            # Используем функцию create_application_message из модуля bot
            from bot.utils.applications import create_application_message
            
            # Получаем Discord ID из данных заявки
            discord_id = application_data.get('discord_id')
            
            # Создаем объект для будущего результата
            future = asyncio.run_coroutine_threadsafe(
                create_application_message(
                    app.bot.channel_for_applications, 
                    discord_id,  # Передаем Discord ID пользователя
                    embed
                ),
                app.bot.loop
            )
            
            # Получаем результат (с таймаутом)
            try:
                result = future.result(timeout=10.0)
                logger.info(f"Обработка заявки успешно завершена: {result}")
                return result
            except asyncio.TimeoutError:
                logger.error("Превышен таймаут обработки заявки")
                return False
            except Exception as e:
                logger.error(f"Ошибка при получении результата обработки заявки: {e}")
                return False
        else:
            logger.warning("Экземпляр бота недоступен. Заявка не будет обработана через Discord.")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при обработке заявки через Discord бота: {e}")
        return False

# Функция для взаимодействия с Discord ботом
def process_donation_in_discord(nickname, amount):
    """
    Асинхронно вызывает обработку доната в Discord боте
    
    Args:
        nickname: Никнейм игрока
        amount: Сумма доната
    """
    try:
        logger.info(f"Обработка доната для {nickname} на сумму {amount}")
        
        # Проверяем, есть ли доступ к экземпляру бота
        if hasattr(app, 'bot') and app.bot is not None:
            import asyncio
            
            # Создаем объект для будущего результата
            future = asyncio.run_coroutine_threadsafe(
                app.bot.handle_donation(nickname, int(amount)),
                app.bot.loop
            )
            
            # Получаем результат (с таймаутом)
            try:
                result = future.result(timeout=10.0)
                logger.info(f"Обработка доната успешно завершена: {result}")
            except asyncio.TimeoutError:
                logger.error("Превышен таймаут обработки доната")
            except Exception as e:
                logger.error(f"Ошибка при получении результата обработки доната: {e}")
            
            logger.info(f"Запрос на обработку доната для {nickname} на сумму {amount} отправлен в бота")
        else:
            logger.warning("Экземпляр бота недоступен. Донат не будет обработан через Discord.")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке доната через Discord бота: {e}")
        # Не поднимаем исключение, чтобы не прерывать обработку успешного платежа

# Обработка вебхуков от ЮMoney
@app.route('/yoomoney-notification', methods=['POST'])
def yoomoney_notification():
    try:
        data = request.form.to_dict()
        logger.debug(f"Получено уведомление от ЮMoney: {data}")
        
        # Проверка подлинности запроса
        if not verify_yoomoney_notification(data):
            logger.warning(f"Получен недействительный вебхук от ЮMoney - подпись не прошла проверку")
            return 'Invalid notification signature', 400
        
        notification_type = data.get('notification_type')
        operation_id = data.get('operation_id')
        amount = data.get('amount')
        label = data.get('label')  # Это наш payment_id
        comment = data.get('comment', '')  # Это никнейм игрока
        
        # Проверяем, не был ли платеж уже обработан
        if payment_already_processed(operation_id):
            logger.info(f"Платеж {operation_id} уже был обработан ранее. Пропускаем.")
            return 'OK', 200
        
        logger.info(f"Валидное уведомление от ЮMoney: тип={notification_type}, операция={operation_id}, платеж={label}, сумма={amount}, комментарий={comment}")
        
        # Обрабатываем донат через бота (только для операций payment.succeeded)
        if notification_type == 'payment.succeeded' and comment and float(amount) > 0:
            process_donation_in_discord(comment, float(amount))
            
            # Сохраняем операцию как обработанную
            mark_payment_as_processed(operation_id)
            
            logger.info(f"Обработан донат через вебхук: игрок={comment}, сумма={amount}")
        
        return 'OK', 200
    except Exception as e:
        logger.exception(f"Ошибка обработки уведомления от ЮMoney: {str(e)}")
        return 'ERROR', 500

def verify_yoomoney_notification(data):
    """
    Проверяет подлинность уведомления от ЮMoney
    
    Args:
        data: Словарь с данными запроса
        
    Returns:
        bool: True если подпись действительна, иначе False
    """
    # Если в тестовом режиме и ключ не настроен - всегда возвращаем True
    if not YOOMONEY_SECRET_KEY:
        logger.warning("Отсутствует секретный ключ ЮMoney - пропускаем проверку подписи")
        return True
    
    try:
        # Создаем строку для проверки подписи
        string_to_check = '&'.join([
            f"{k}={v}" for k, v in data.items() if k != 'sha1_hash'
        ])
        
        # Добавляем секретный ключ
        string_to_check += f"&{YOOMONEY_SECRET_KEY}"
        
        # Вычисляем SHA-1 хеш
        calculated_hash = hashlib.sha1(string_to_check.encode('utf-8')).hexdigest()
        
        # Получаем хеш из запроса
        received_hash = data.get('sha1_hash', '')
        
        # Сравниваем хеши
        return calculated_hash == received_hash
    except Exception as e:
        logger.error(f"Ошибка при проверке подписи ЮMoney: {e}")
        return False

# Хранилище для отслеживания обработанных платежей
processed_payments = set()

def payment_already_processed(operation_id):
    """
    Проверяет, был ли платеж уже обработан
    
    Args:
        operation_id: ID операции ЮMoney
        
    Returns:
        bool: True если платеж уже обработан, иначе False
    """
    return operation_id in processed_payments

def mark_payment_as_processed(operation_id):
    """
    Помечает платеж как обработанный
    
    Args:
        operation_id: ID операции ЮMoney
    """
    processed_payments.add(operation_id)

# Создаем сериализатор для защищенных токенов
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Функция для создания защищенного токена доната
def create_donation_token(nickname, amount, payment_id):
    """
    Создает защищенный токен для доната
    
    Args:
        nickname: Игровой ник
        amount: Сумма доната
        payment_id: ID платежа
        
    Returns:
        str: Защищенный токен
    """
    data = {'nickname': nickname, 'amount': amount, 'payment_id': payment_id, 'timestamp': time.time()}
    return serializer.dumps(data)

# Функция для проверки токена доната
def verify_donation_token(token):
    """
    Проверяет токен доната
    
    Args:
        token: Токен для проверки
        
    Returns:
        dict или None: Данные из токена если токен верен, иначе None
    """
    try:
        # Проверяем токен с ограничением по времени (1 час)
        data = serializer.loads(token, max_age=3600)
        return data
    except (SignatureExpired, BadSignature):
        return None

# ==========================================
# МАРШРУТЫ АУТЕНТИФИКАЦИИ
# ==========================================

@app.route('/login')
def login():
    """Страница входа через Discord"""
    if discord_auth.is_authenticated():
        return redirect(url_for('apply'))
    
    auth_url = discord_auth.get_authorization_url()
    return render_template('login.html', auth_url=auth_url)

@app.route('/auth/discord/callback')
def discord_callback():
    """Обработка callback от Discord OAuth"""
    logger.info("[DISCORD] Получен Discord OAuth callback")
    
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    logger.info(f"[DISCORD] Параметры callback: code={code[:10] if code else None}..., state={state[:10] if state else None}..., error={error}")
    
    if error:
        logger.error(f"[DISCORD] Discord OAuth ошибка: {error}")
        return redirect(url_for('login'))
    
    if not code or not state:
        logger.error("[DISCORD] Отсутствует код авторизации или state")
        return redirect(url_for('login'))
    
    try:
        logger.info("[DISCORD] Обмен кода на токен...")
        # Обмениваем код на токен
        token_data = discord_auth.exchange_code_for_token(code, state)
        access_token = token_data['access_token']
        
        logger.info("[DISCORD] Получение информации о пользователе...")
        # Получаем информацию о пользователе
        user_data = discord_auth.get_user_info(access_token)
        
        logger.info("[DISCORD] Проверка членства в сервере...")
        # Проверяем членство в сервере
        is_guild_member = discord_auth.check_guild_membership(access_token, user_data['id'])
        
        logger.info("[DISCORD] Создание сессии пользователя...")
        # Создаем сессию
        discord_auth.create_user_session(user_data, is_guild_member, access_token)
        
        logger.info(f"[DISCORD] Успешная авторизация пользователя: {user_data['username']}")
        
        # Проверим сессию после создания
        logger.info(f"[DISCORD] Session сразу после создания: {dict(session)}")
        
        # Перенаправляем в зависимости от членства в сервере
        if is_guild_member:
            logger.info("[DISCORD] Пользователь - участник сервера, перенаправление на /apply")
            return redirect(url_for('apply'))
        else:
            logger.info("[DISCORD] Пользователь не участник сервера, перенаправление на /join-server")
            return redirect(url_for('join_server'))
            
    except Exception as e:
        logger.error(f"[DISCORD] Ошибка в Discord callback: {e}")
        import traceback
        logger.error(f"[DISCORD] Трейс: {traceback.format_exc()}")
        return redirect(url_for('login'))

@app.route('/join-server')
@require_auth
def join_server():
    """Страница для присоединения к Discord серверу"""
    current_user = discord_auth.get_current_user()
    
    # Если уже участник, перенаправляем к заявке
    if current_user and current_user['guild_member']:
        return redirect(url_for('apply'))
    
    discord_invite_url = "https://discord.com/invite/yNz87pJZPh"  # Обновите на вашу ссылку
    return render_template('join_server.html', 
                         current_user=current_user,
                         discord_invite_url=discord_invite_url)

@app.route('/check-membership')
@require_auth
def check_membership():
    """Проверка членства в Discord сервере"""
    if discord_auth.refresh_guild_membership():
        return redirect(url_for('apply'))
    else:
        return redirect(url_for('join_server'))

@app.route('/application-pending')
@require_auth
def application_pending():
    """Страница ожидающей заявки"""
    current_user = discord_auth.get_current_user()
    
    # Получаем актуальный статус заявки из файла
    if current_user:
        application_status_data = get_application_status(current_user['user_id'])
        if application_status_data:
            current_user['application_status'] = application_status_data['status']
            current_user['application_reason'] = application_status_data.get('reason', '')
            current_user['application_timestamp'] = application_status_data.get('timestamp')
        else:
            # Если статуса нет в файле, очищаем сессию и перенаправляем на подачу заявки
            if 'application_status' in session:
                session.pop('application_status', None)
                logger.info(f"Очищен устаревший статус заявки из сессии для пользователя {current_user['user_id']}")
            return redirect(url_for('apply'))
    
    return render_template('application_pending.html', current_user=current_user)

@app.route('/logout')
def logout():
    """Выход из системы"""
    discord_auth.logout()
    return redirect(url_for('index'))

@app.route('/admin')
@require_auth
def admin_panel():
    """Панель администратора"""
    # Проверяем и обновляем права доступа (только для доступа к админ-панели)
    if not check_and_update_admin_permissions():
        return redirect(url_for('index'))
    
    return render_template('admin_panel.html')

# Тестовый маршрут для админ-панели (без авторизации)
@app.route('/admin-test')
def admin_panel_test():
    """Тестовая панель администратора без авторизации"""
    return render_template('admin_panel.html')

# Тестовый API для админ-панели (без авторизации)
@app.route('/api/config-test')
def get_bot_config_test():
    """Тестовый API для конфигурации бота без авторизации"""
    try:
        from bot.config_manager import get_config
        config = get_config()
        # Используем метод get_admin_panel_config для получения структурированной конфигурации
        config_dict = config.get_admin_panel_config()
        return jsonify(config_dict)
    except Exception as e:
        logger.error(f"Ошибка при получении конфигурации: {e}")
        return jsonify({"error": str(e)}), 500

# Context processor для передачи информации о пользователе во все шаблоны
@app.context_processor
def inject_user():
    """Добавляет информацию о текущем пользователе во все шаблоны"""
    logger.debug(f"[CONTEXT] Context processor: session = {dict(session)}")
    logger.debug(f"[CONTEXT] Context processor: is_authenticated = {discord_auth.is_authenticated()}")
    
    current_user = None
    if discord_auth.is_authenticated():
        current_user = discord_auth.get_current_user()
        logger.debug(f"[CONTEXT] Context processor: current_user = {current_user}")
    
    return {'current_user': current_user}

def get_application_status(discord_id):
    """Получает статус заявки для указанного Discord ID"""
    try:
        status_file_path = os.path.join(os.path.dirname(__file__), 'application_statuses.json')
        
        if not os.path.exists(status_file_path):
            return None
            
        with open(status_file_path, 'r', encoding='utf-8') as f:
            statuses = json.load(f)
            
        return statuses.get(str(discord_id))
        
    except Exception as e:
        logger.error(f"Ошибка при получении статуса заявки для {discord_id}: {e}")
        return None


def save_application_status(discord_id, status, reason=""):
    """Сохраняет статус заявки для указанного Discord ID"""
    try:
        status_file_path = os.path.join(os.path.dirname(__file__), 'application_statuses.json')
        
        # Читаем существующие статусы или создаем пустой словарь
        if os.path.exists(status_file_path):
            with open(status_file_path, 'r', encoding='utf-8') as f:
                statuses = json.load(f)
        else:
            statuses = {}
        
        # Добавляем/обновляем статус
        statuses[str(discord_id)] = {
            'status': status,
            'timestamp': time.time(),
            'reason': reason
        }
        
        # Сохраняем обратно в файл
        with open(status_file_path, 'w', encoding='utf-8') as f:
            json.dump(statuses, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Сохранен статус заявки для Discord ID {discord_id}: {status}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении статуса заявки для {discord_id}: {e}")
        return False


@app.route('/api/application-status', methods=['POST'])
def api_get_application_status():
    """API endpoint для получения статуса заявки"""
    try:
        # Проверка авторизации
        api_key = request.headers.get('X-API-Key')
        expected_api_key = os.getenv('INTERNAL_API_KEY', 'your-secret-api-key')
        if api_key != expected_api_key:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Получение данных из запроса
        data = request.get_json()
        if not data or 'discord_id' not in data:
            return jsonify({'error': 'Missing discord_id'}), 400
        
        discord_id = str(data['discord_id'])
        
        # Получение статуса заявки
        status_data = get_application_status(discord_id)
        
        if status_data is None:
            return jsonify({'status': None, 'has_application': False}), 200
        
        return jsonify({
            'status': status_data.get('status'),
            'has_application': True,
            'timestamp': status_data.get('timestamp'),
            'reason': status_data.get('reason', '')
        }), 200
        
    except Exception as e:
        logger.error(f"Ошибка в API получения статуса заявки: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/debug/dropdown')
def debug_dropdown():
    """Debug page for dropdown functionality"""
    return render_template('debug_dropdown.html')

@app.route('/debug/dropdown-with-user')
def debug_dropdown_with_user():
    """Debug page for dropdown functionality with a fake user"""
    # Create fake user data for testing
    fake_user = {
        'user_id': '123456789',
        'username': 'testuser#1234',
        'display_name': 'Test User',
        'avatar_url': 'https://cdn.discordapp.com/avatars/123456789/abc123.png',
        'guild_member': True,
        'application_status': None,
        'login_time': '2025-06-28T16:48:00'
    }
    return render_template('debug_dropdown.html', current_user=fake_user)


# === API ДЛЯ АДМИН-ПАНЕЛИ ===

from bot.config_manager import get_config, reload_config

def check_and_update_admin_permissions():
    """Проверяет и обновляет права администратора текущего пользователя"""
    if 'access_token' not in session or 'user_id' not in session:
        return False
    
    # Используем кэшированное значение, если оно есть и не устарело
    is_admin_cached = session.get('is_admin', False)
    last_check = session.get('admin_check_time')
    
    if is_admin_cached and last_check:
        try:
            last_check_time = datetime.fromisoformat(last_check)
            # Если последняя проверка была менее 10 минут назад, используем кэшированное значение
            if datetime.now() - last_check_time < timedelta(minutes=10):
                app.logger.debug("Используем кэшированное значение прав администратора")
                return is_admin_cached
        except (ValueError, TypeError):
            pass  # Если время некорректное, делаем новую проверку
    
    # Только если кэш устарел, делаем новую проверку
    try:
        discord_auth = current_app.discord_auth
        is_admin = discord_auth.check_admin_permissions(session['access_token'], session['user_id'])
        
        # Сохраняем в сессии с временной меткой
        session['is_admin'] = is_admin
        session['admin_check_time'] = datetime.now().isoformat()
        session.modified = True
        
        return is_admin
    except Exception as e:
        app.logger.error(f"Ошибка при проверке прав администратора: {e}")
        # Если произошла ошибка, используем кэшированное значение
        return is_admin_cached

def is_admin_cached():
    """Проверяет права администратора только из кэша сессии, без обращения к Discord API"""
    return session.get('is_admin', False)

@app.route('/api/user', methods=['GET'])
def get_current_user():
    """Получение информации о текущем пользователе"""
    try:
        # Проверяем, есть ли авторизованный пользователь
        if not discord_auth.is_authenticated():
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'No user ID in session'}), 401
        
        # Возвращаем информацию о пользователе из сессии
        return jsonify({
            'id': user_id,
            'username': session.get('username', 'Unknown'),
            'display_name': session.get('display_name', 'Unknown'),
            'avatar_url': session.get('avatar_url', ''),
            'is_admin': is_admin_cached(),
            'authenticated': True
        })
    
    except Exception as e:
        app.logger.error(f"Ошибка при получении информации о пользователе: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/config', methods=['GET'])
@require_auth
def get_bot_config():
    """Получение конфигурации бота для админ-панели"""
    try:
        # Проверяем права доступа только из кэша
        if not is_admin_cached():
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        config = get_config()
        # Используем упрощенную структуру для совместимости с JavaScript
        simple_config = config.get_simple_config()
        
        return jsonify(simple_config)
    except Exception as e:
        app.logger.error(f"Ошибка при получении конфигурации: {e}")
        return jsonify({'error': 'Failed to retrieve configuration'}), 500


@app.route('/api/config', methods=['POST'])
@require_auth
def update_bot_config():
    """Обновление конфигурации бота через админ-панель"""
    try:
        # Проверяем права доступа только из кэша
        if not is_admin_cached():
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400
        
        config = get_config()
        
        # Обновляем конфигурацию целиком
        # Преобразуем flat structure в updates для update_multiple
        updates = {}
        
        # Discord роли
        if 'discord' in data and 'roles' in data['discord']:
            for role_name, role_id in data['discord']['roles'].items():
                updates[f'discord.roles.{role_name}'] = role_id
        
        # Discord каналы
        if 'discord' in data and 'channels' in data['discord']:
            for channel_name, channel_id in data['discord']['channels'].items():
                updates[f'discord.channels.{channel_name}'] = channel_id
        
        # Настройки донатов
        if 'donations' in data:
            donations = data['donations']
            if 'enabled' in donations:
                updates['donations.enabled'] = donations['enabled']
            
            if 'thresholds' in donations:
                for threshold_name, threshold_value in donations['thresholds'].items():
                    updates[f'donations.thresholds.{threshold_name}'] = threshold_value
            
            if 'rewards' in donations:
                for reward_name, reward_value in donations['rewards'].items():
                    updates[f'donations.rewards.{reward_name}'] = reward_value
            
            if 'minecraft_commands' in donations:
                for command_name, command_value in donations['minecraft_commands'].items():
                    updates[f'donations.minecraft_commands.{command_name}'] = command_value
        
        # Системные настройки
        if 'system' in data:
            system = data['system']
            if 'timeouts' in system:
                for timeout_name, timeout_value in system['timeouts'].items():
                    updates[f'system.timeouts.{timeout_name}'] = timeout_value
            
            if 'application' in system:
                for app_name, app_value in system['application'].items():
                    updates[f'system.application.{app_name}'] = app_value
        
        # Обновляем настройки
        if updates:
            success = config.update_multiple(updates, save=True)
            
            if success:
                # Перезагружаем конфигурацию для применения изменений
                reload_config()
                
                return jsonify({
                    'success': True,
                    'message': 'Configuration updated successfully',
                    'updated_count': len(updates)
                })
            else:
                return jsonify({'error': 'Failed to update configuration'}), 500
        else:
            return jsonify({'error': 'No valid updates provided'}), 400
            
    except Exception as e:
        app.logger.error(f"Ошибка при обновлении конфигурации: {e}")
        return jsonify({'error': 'Failed to update configuration'}), 500


@app.route('/api/config/reload', methods=['POST'])
@require_auth
def reload_bot_config():
    """Перезагрузка конфигурации бота из файла"""
    try:
        # Проверяем права доступа только из кэша
        if not is_admin_cached():
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        # Перезагружаем конфигурацию
        config = reload_config()
        
        return jsonify({
            'success': True,
            'message': 'Configuration reloaded successfully',
            'updated_at': config.get('_metadata.updated_at')
        })
        
    except Exception as e:
        app.logger.error(f"Ошибка при перезагрузке конфигурации: {e}")
        return jsonify({'error': 'Failed to reload configuration'}), 500


@app.route('/api/config/validate', methods=['GET'])
@require_auth
def validate_bot_config():
    """Валидация конфигурации бота"""
    try:
        # Проверяем права доступа только из кэша
        if not is_admin_cached():
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        config = get_config()
        validation_results = config.validate_discord_ids()
        
        # Подсчитываем результаты
        valid_count = sum(1 for v in validation_results.values() if v)
        total_count = len(validation_results)
        
        return jsonify({
            'success': True,
            'validation': validation_results,
            'summary': {
                'valid_count': valid_count,
                'total_count': total_count,
                'is_valid': valid_count == total_count
            }
        })
        
    except Exception as e:
        app.logger.error(f"Ошибка при валидации конфигурации: {e}")
        return jsonify({'error': 'Failed to validate configuration'}), 500


if __name__ == '__main__':
    app.run(debug=True)