import pytest
import sys
import os

# Добавляем корневую директорию проекта в путь Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

@pytest.fixture
def client():
    """Фикстура для создания тестового клиента Flask."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """Тест главной страницы."""
    response = client.get('/')
    assert response.status_code == 200

def test_about_route(client):
    """Тест страницы about."""
    response = client.get('/about')
    assert response.status_code == 200

def test_rules_route(client):
    """Тест страницы rules."""
    response = client.get('/rules')
    assert response.status_code == 200

def test_build_route(client):
    """Тест страницы build."""
    response = client.get('/build')
    assert response.status_code == 200

def test_apply_route(client):
    """Тест страницы apply - проверяем редирект на авторизацию."""
    response = client.get('/apply')
    # Страница подачи заявки требует авторизации, поэтому ожидаем редирект
    assert response.status_code == 302
    assert '/login' in response.location or '/auth/discord' in response.location