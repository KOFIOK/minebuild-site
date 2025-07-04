"""
Модуль аутентификации через Discord OAuth 2.0
Обеспечивает авторизацию пользователей и проверку членства в Discord сервере
"""

import requests
import secrets
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode
from flask import session, request, redirect, url_for, current_app
from functools import wraps

# Импортируем функцию для получения ID роли модератора
from bot.config_manager import get_moderator_role_id

# Настройка логгера
logger = logging.getLogger(__name__)

class DiscordAuth:
    """Класс для работы с Discord OAuth 2.0"""
    
    def __init__(self, app=None, bot_instance=None):
        self.app = app
        self.bot = bot_instance
        
        # Discord OAuth настройки
        self.CLIENT_ID = None
        self.CLIENT_SECRET = None
        self.REDIRECT_URI = None
        self.GUILD_ID = None
        
        # Discord API endpoints
        self.DISCORD_API_BASE = "https://discord.com/api/v10"
        self.OAUTH_URL = "https://discord.com/api/oauth2/authorize"
        self.TOKEN_URL = "https://discord.com/api/oauth2/token"
        
        if app is not None:
            self.init_app(app, bot_instance)
    
    def init_app(self, app, bot_instance=None):
        """Инициализация с Flask приложением"""
        self.app = app
        self.bot = bot_instance
        
        # Загружаем конфигурацию
        self.CLIENT_ID = app.config.get('DISCORD_CLIENT_ID')
        self.CLIENT_SECRET = app.config.get('DISCORD_CLIENT_SECRET') 
        self.REDIRECT_URI = app.config.get('DISCORD_REDIRECT_URI')
        self.GUILD_ID = app.config.get('DISCORD_GUILD_ID')
        
        # Настройки сессий (НЕ переопределяем, если уже установлены в app.py)
        if not app.config.get('PERMANENT_SESSION_LIFETIME'):
            app.permanent_session_lifetime = timedelta(days=30)
        
        logger.info("Discord Auth модуль инициализирован")
    
    def get_authorization_url(self):
        """Генерирует URL для авторизации Discord"""
        state = secrets.token_urlsafe(32)
        logger.info(f"[AUTH] Создание нового state: {state}")
        logger.info(f"[AUTH] Session до сохранения state: {dict(session)}")
        
        session['oauth_state'] = state
        session.permanent = True  # Убедимся что сессия permanent
        session.modified = True   # Принудительно помечаем как измененную
        
        logger.info(f"[AUTH] Session после сохранения state: {dict(session)}")
        
        params = {
            'client_id': self.CLIENT_ID,
            'redirect_uri': self.REDIRECT_URI,
            'response_type': 'code',
            'scope': 'identify guilds guilds.members.read',
            'state': state
        }
        
        auth_url = f"{self.OAUTH_URL}?{urlencode(params)}"
        logger.info(f"Создан URL авторизации:")
        logger.info(f"  Client ID: {self.CLIENT_ID}")
        logger.info(f"  Redirect URI: {self.REDIRECT_URI}")
        logger.info(f"  State: {state}")
        logger.info(f"  Полный URL: {auth_url}")
        return auth_url
    
    def exchange_code_for_token(self, code, state):
        """Обменивает authorization code на access token"""
        logger.info(f"[AUTH] Проверка state: получен={state}, в сессии={session.get('oauth_state')}")
        logger.info(f"[AUTH] Session содержимое при проверке state: {dict(session)}")
        
        # Проверяем state для защиты от CSRF
        if state != session.get('oauth_state'):
            logger.warning(f"[AUTH] Неверный state в OAuth callback: получен={state}, ожидался={session.get('oauth_state')}")
            raise ValueError("Invalid state parameter")
        
        # Удаляем state из сессии
        session.pop('oauth_state', None)
        
        data = {
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.REDIRECT_URI
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = requests.post(self.TOKEN_URL, data=data, headers=headers, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            logger.info("Успешно получен access token")
            return token_data
            
        except requests.RequestException as e:
            logger.error(f"Ошибка при получении токена: {e}")
            raise
    
    def get_user_info(self, access_token):
        """Получает информацию о пользователе"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Получаем основную информацию о пользователе
            response = requests.get(f"{self.DISCORD_API_BASE}/users/@me", 
                                  headers=headers, timeout=10)
            response.raise_for_status()
            user_data = response.json()
            
            logger.info(f"Получена информация о пользователе: {user_data['username']}")
            return user_data
            
        except requests.RequestException as e:
            logger.error(f"Ошибка при получении информации о пользователе: {e}")
            raise
    
    def check_guild_membership(self, access_token, user_id):
        """Проверяет членство пользователя в Discord сервере"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            logger.info(f"[GUILD_CHECK] Проверка членства для пользователя {user_id} в сервере {self.GUILD_ID}")
            
            # Получаем список серверов пользователя
            response = requests.get(f"{self.DISCORD_API_BASE}/users/@me/guilds", 
                                  headers=headers, timeout=10)
            response.raise_for_status()
            guilds = response.json()
            
            logger.info(f"[GUILD_CHECK] Пользователь состоит в {len(guilds)} серверах")
            logger.info(f"[GUILD_CHECK] Список серверов пользователя:")
            for guild in guilds:
                logger.info(f"[GUILD_CHECK]   - {guild['name']} (ID: {guild['id']})")
            
            # Проверяем, есть ли наш сервер в списке
            target_guild_id = str(self.GUILD_ID)
            is_member = any(guild['id'] == target_guild_id for guild in guilds)
            
            logger.info(f"[GUILD_CHECK] Ищем сервер с ID: {target_guild_id}")
            logger.info(f"[GUILD_CHECK] Результат проверки: {'УЧАСТНИК' if is_member else 'НЕ УЧАСТНИК'}")
            
            if is_member:
                logger.info(f"Пользователь {user_id} является участником сервера")
            else:
                logger.warning(f"Пользователь {user_id} НЕ является участником сервера {target_guild_id}")
                logger.warning(f"Возможные причины:")
                logger.warning(f"  1. Неверный GUILD_ID в .env файле")
                logger.warning(f"  2. Пользователь действительно не на сервере")
                logger.warning(f"  3. У бота нет прав 'View Server Members'")
            
            return is_member
            
        except requests.RequestException as e:
            logger.error(f"Ошибка при проверке членства в сервере: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"HTTP статус: {e.response.status_code}")
                logger.error(f"Ответ: {e.response.text}")
            return False
    
    def create_user_session(self, user_data, guild_member, access_token):
        """Создает сессию пользователя"""
        # Обрабатываем новый формат Discord username (без discriminator)
        discriminator = user_data.get('discriminator', '0')
        if discriminator == '0' or discriminator is None:
            username_display = user_data['username']
        else:
            username_display = f"{user_data['username']}#{discriminator}"
        
        logger.info(f"[SESSION] Создание сессии для пользователя {username_display}")
        logger.info(f"[SESSION] Session до изменений: {dict(session)}")
        
        session.permanent = True
        
        # Генерируем URL аватара
        avatar_url = None
        if user_data.get('avatar'):
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png?size=128"
        else:
            # Дефолтный аватар Discord (новая система)
            if discriminator == '0' or discriminator is None:
                # Новая система Discord - используем user_id для вычисления
                default_avatar = (int(user_data['id']) >> 22) % 6
            else:
                # Старая система Discord
                default_avatar = int(discriminator) % 5
            avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_avatar}.png"
        
        session_data = {
            'user_id': user_data['id'],
            'username': username_display,
            'display_name': user_data['username'],
            'avatar_url': avatar_url,
            'guild_member': guild_member,
            'is_admin': self.check_admin_permissions(access_token, user_data['id']) if guild_member else False,
            'admin_check_time': datetime.now().isoformat(),  # Время последней проверки прав
            'last_check': datetime.now().isoformat(),
            'login_time': datetime.now().isoformat(),
            'application_status': self.get_application_status(user_data['id']),
            'access_token': access_token  # Сохраняем для периодических проверок
        }
        
        # Очищаем сессию и добавляем новые данные
        session.clear()
        session.update(session_data)
        
        logger.info(f"[SESSION] Создана сессия для пользователя {username_display}")
        logger.info(f"[SESSION] Данные сессии: {list(session_data.keys())}")
        logger.info(f"[SESSION] Session permanent: {session.permanent}")
        logger.info(f"[SESSION] Session data после обновления: {dict(session)}")
        
        # Принудительно сохраняем сессию
        session.modified = True
    
    def get_application_status(self, user_id):
        """Получает статус заявки пользователя через бота"""
        try:
            if self.bot and hasattr(self.bot, 'get_user_application_status'):
                return self.bot.get_user_application_status(user_id)
        except Exception as e:
            logger.error(f"Ошибка при получении статуса заявки: {e}")
        
        return None
    
    def refresh_guild_membership(self):
        """Обновляет информацию о членстве в сервере"""
        if 'access_token' not in session:
            logger.warning("[MEMBERSHIP] Нет access token для обновления членства")
            return False
        
        try:
            user_id = session['user_id']
            access_token = session['access_token']
            
            logger.info(f"[MEMBERSHIP] Обновление статуса членства для пользователя {user_id}")
            
            # Проверяем актуальность токена и членство
            is_member = self.check_guild_membership(access_token, user_id)
            
            # Обновляем данные в сессии
            session['guild_member'] = is_member
            session['last_check'] = datetime.now().isoformat()
            session.modified = True
            
            logger.info(f"[MEMBERSHIP] Обновлен статус членства: {'УЧАСТНИК' if is_member else 'НЕ УЧАСТНИК'}")
            
            # ИЗМЕНЕНИЕ: НЕ разлогиниваем пользователя, если он не участник сервера
            # Пользователь может быть авторизован, но еще не присоединился к серверу
            # Разлогинивание должно происходить только при ошибках токена или других критических проблемах
            
            return is_member
            
        except Exception as e:
            logger.error(f"[MEMBERSHIP] Ошибка при обновлении членства: {e}")
            # При ошибке разлогиниваем для безопасности (например, если токен недействителен)
            logger.warning("[MEMBERSHIP] Разлогинивание из-за ошибки обновления членства")
            self.logout()
            return False
    
    def logout(self):
        """Выход из системы"""
        user_id = session.get('user_id', 'unknown')
        session.clear()
        logger.info(f"Пользователь {user_id} разлогинен")
    
    def is_authenticated(self):
        """Проверяет, авторизован ли пользователь"""
        return 'user_id' in session
    
    def is_guild_member(self):
        """Проверяет, является ли пользователь участником сервера"""
        return session.get('guild_member', False)
    
    def check_admin_permissions(self, access_token, user_id):
        """Проверяет, имеет ли пользователь права администратора"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Получаем информацию о пользователе на сервере
            response = requests.get(
                f"{self.DISCORD_API_BASE}/users/@me/guilds/{self.GUILD_ID}/member",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                member_data = response.json()
                user_roles = member_data.get('roles', [])
                
                # Получаем ID роли модератора из конфигурации
                moderator_role_id_raw = get_moderator_role_id()
                moderator_role_id = str(moderator_role_id_raw)
                
                logger.info(f"[ADMIN_CHECK] Пользователь {user_id}: роли {user_roles}")
                logger.info(f"[ADMIN_CHECK] Роль модератора (сырая): {moderator_role_id_raw} (тип: {type(moderator_role_id_raw)})")
                logger.info(f"[ADMIN_CHECK] Роль модератора (строка): {moderator_role_id}")
                
                # Проверяем, есть ли у пользователя роль модератора
                is_admin = moderator_role_id in user_roles
                logger.info(f"[ADMIN_CHECK] Права администратора: {'ДА' if is_admin else 'НЕТ'}")
                
                return is_admin
            else:
                logger.warning(f"[ADMIN_CHECK] Не удалось получить информацию о пользователе: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"[ADMIN_CHECK] Ошибка при проверке прав администратора: {e}")
            return False
    
    def is_admin(self):
        """Проверяет, имеет ли текущий пользователь права администратора"""
        return session.get('is_admin', False)
    
    def get_current_user(self):
        """Возвращает данные текущего пользователя"""
        if not self.is_authenticated():
            return None
        
        return {
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'display_name': session.get('display_name'),
            'avatar_url': session.get('avatar_url'),
            'guild_member': session.get('guild_member', False),
            'is_admin': session.get('is_admin', False),
            'application_status': session.get('application_status'),
            'login_time': session.get('login_time')
        }
    
    def update_application_status(self, status):
        """Обновляет статус заявки в сессии"""
        session['application_status'] = status
        logger.info(f"Обновлен статус заявки для пользователя {session.get('user_id')}: {status}")

# Декораторы для проверки авторизации
def require_auth(f):
    """Декоратор для маршрутов, требующих авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = current_app.discord_auth
        
        logger.info(f"[AUTH] Проверка авторизации для {f.__name__}")
        logger.info(f"[AUTH] Session содержимое: {dict(session)}")
        logger.info(f"[AUTH] is_authenticated(): {auth.is_authenticated()}")
        logger.info(f"[AUTH] user_id в сессии: {'user_id' in session}")
        
        if not auth.is_authenticated():
            logger.info("[AUTH] Неавторизованный доступ, перенаправление на логин")
            return redirect(url_for('login'))
        
        # Проверяем, не нужно ли обновить информацию о членстве
        last_check = session.get('last_check')
        if last_check:
            last_check_time = datetime.fromisoformat(last_check)
            # Проверяем каждый час
            if datetime.now() - last_check_time > timedelta(hours=1):
                logger.info("[AUTH] Обновление информации о членстве в сервере")
                if not auth.refresh_guild_membership():
                    return redirect(url_for('login'))
        
        logger.info(f"[AUTH] Авторизация пройдена для {f.__name__}")
        return f(*args, **kwargs)
    return decorated_function

def require_guild_member(f):
    """Декоратор для маршрутов, требующих членства в Discord сервере"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = current_app.discord_auth
        
        if not auth.is_authenticated():
            return redirect(url_for('login'))
        
        if not auth.is_guild_member():
            logger.info("Пользователь не является участником сервера")
            return redirect(url_for('join_server'))
        
        return f(*args, **kwargs)
    return decorated_function

def can_submit_application(f):
    """Декоратор для проверки возможности подать заявку"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = current_app.discord_auth
        current_user = auth.get_current_user()
        
        if not current_user:
            return redirect(url_for('login'))
        
        # Проверяем актуальный статус заявки из файла
        from app import get_application_status
        application_status_data = get_application_status(current_user['user_id'])
        
        if application_status_data:
            app_status = application_status_data['status']
            # Блокируем подачу заявки если статус: pending или candidate
            # Разрешаем только если: approved, rejected, или нет статуса
            if app_status in ['pending', 'candidate']:
                logger.info(f"Пользователь {current_user['user_id']} пытается подать заявку повторно (статус: {app_status})")
                return redirect(url_for('application_pending'))
        else:
            # Если статуса нет в файле, очищаем сессию
            if 'application_status' in session:
                session.pop('application_status', None)
                logger.info(f"Очищен устаревший статус заявки из сессии для пользователя {current_user['user_id']}")
        
        return f(*args, **kwargs)
    return decorated_function
