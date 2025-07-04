import sys
import os
import pytest
import warnings
from dotenv import load_dotenv

# Добавляем корневую директорию проекта в путь Python для всех тестов
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Загружаем тестовые переменные окружения
test_env_path = os.path.join(os.path.dirname(__file__), '..', '.env.test')
if os.path.exists(test_env_path):
    load_dotenv(test_env_path)

# Устанавливаем флаг тестирования
os.environ['TESTING'] = 'true'

# Фильтруем предупреждения
def pytest_configure(config):
    # Игнорируем предупреждение о устаревшем модуле audioop в discord.py
    warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*audioop.*")

# Можно добавить общие фикстуры здесь, которые будут доступны всем тестам