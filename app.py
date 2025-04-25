from flask import Flask, render_template, request, jsonify, redirect, url_for
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
        data = request.json
        logger.debug(f"Получены данные из формы: {data}")
        
        # Валидация данных
        if not data or 'amount' not in data or 'comment' not in data:
            logger.error("Неверные параметры запроса: отсутствуют обязательные поля")
            return jsonify({'success': False, 'error': 'Неверные параметры запроса'}), 400
        
        amount = float(data['amount'])
        nickname = data['comment']  # Получаем ник из поля comment, как передает frontend
        payment_type = data.get('payment_type', 'AC')  # По умолчанию - банковская карта
        
        if amount < 1:
            logger.warning(f"Попытка создать платеж на сумму меньше минимальной: {amount}")
            return jsonify({'success': False, 'error': 'Минимальная сумма - 1 ₽'}), 400
        
        # Создаем уникальный идентификатор для платежа
        payment_id = str(uuid.uuid4())
        
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
            "successURL": SUCCESS_URL,
            "need-fio": "false",
            "need-email": "false",
            "need-phone": "false",
            "need-address": "false"
        }
        
        # Формируем URL для редиректа на форму ЮMoney
        quickpay_url = "https://yoomoney.ru/quickpay/confirm.xml"
        
        # В реальном приложении здесь можно сохранить информацию о платеже в базу данных
        logger.info(f"Создан платеж: ID={payment_id}, Игрок={nickname}, Сумма={amount}")
        
        # Логирование параметров запроса
        logger.debug(f"Параметры запроса: {quickpay_form}")
        
        # Возвращаем данные для формирования URL на фронтенде
        return jsonify({
            'success': True,
            'payment_id': payment_id,
            'redirect_url': f"{quickpay_url}?{requests.compat.urlencode(quickpay_form)}"
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
        # Получаем параметры из URL после оплаты ЮMoney
        label = request.args.get('label', '')
        amount = request.args.get('sum', 0)
        nickname = request.args.get('comment', '')
        
        # Логируем информацию о платеже
        logger.info(f"Успешный платеж: label={label}, сумма={amount}, игрок={nickname}")
        
        # Асинхронно обрабатываем донат через Discord бота
        process_donation_in_discord(nickname, float(amount))
        
        # Рендерим страницу успеха с параметрами
        return render_template('donation_success.html', 
                              nickname=nickname,
                              amount=amount)
    except Exception as e:
        logger.exception(f"Ошибка при обработке успешного платежа: {str(e)}")
        return render_template('donation_success.html')

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
        import asyncio
        import threading
        from bot import handle_donation
        
        # Создаем и запускаем асинхронную задачу в отдельном потоке
        def run_async_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(handle_donation(nickname, int(amount)))
            loop.close()
        
        # Запускаем в отдельном потоке, чтобы не блокировать веб-приложение
        thread = threading.Thread(target=run_async_task)
        thread.daemon = True  # Поток завершится вместе с основным потоком
        thread.start()
        
        logger.info(f"Запущена обработка доната для {nickname} на сумму {amount} через Discord")
    except Exception as e:
        logger.error(f"Ошибка при обращении к Discord боту: {str(e)}")
        # Не поднимаем исключение, чтобы не прерывать обработку успешного платежа

# Обработка вебхуков от ЮMoney (требуется настройка в кабинете ЮMoney)
@app.route('/yoomoney-notification', methods=['POST'])
def yoomoney_notification():
    try:
        data = request.form
        logger.debug(f"Получено уведомление от ЮMoney: {data}")
        
        # Проверка подлинности запроса (требуется настраивать на основе рекомендаций ЮMoney)
        # В простой версии просто логируем уведомления
        
        notification_type = data.get('notification_type')
        operation_id = data.get('operation_id')
        amount = data.get('amount')
        label = data.get('label')  # Это наш payment_id
        comment = data.get('comment', '')  # Это никнейм игрока
        
        logger.info(f"Уведомление: тип={notification_type}, платеж={label}, сумма={amount}, комментарий={comment}")
        
        # Здесь можно добавить логику для активации привилегий в игре
        
        return 'OK', 200
    except Exception as e:
        logger.exception(f"Ошибка обработки уведомления: {str(e)}")
        return 'ERROR', 500

if __name__ == '__main__':
    app.run(debug=True)