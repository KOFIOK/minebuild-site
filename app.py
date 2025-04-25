from flask import Flask, render_template, request, jsonify, redirect, url_for, session, make_response
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import requests
import json
import logging
import hashlib
import time
import uuid
from datetime import datetime
import os
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

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
def apply():
    return render_template('apply.html')

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
        
        if amount < 1:
            logger.warning(f"Попытка создать платеж на сумму меньше минимальной: {amount}")
            return jsonify({'success': False, 'error': 'Минимальная сумма - 1 ₽'}), 400
        
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

if __name__ == '__main__':
    app.run(debug=True)