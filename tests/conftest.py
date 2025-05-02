import sys
import os
import pytest
import warnings

# Добавляем корневую директорию проекта в путь Python для всех тестов
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Фильтруем предупреждения
def pytest_configure(config):
    # Игнорируем предупреждение о устаревшем модуле audioop в discord.py
    warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*audioop.*")

# Можно добавить общие фикстуры здесь, которые будут доступны всем тестам