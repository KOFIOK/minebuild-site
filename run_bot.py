#!/usr/bin/env python3
"""
Точка входа для запуска Discord бота MineBuild

Этот скрипт запускает модулярную версию бота из директории bot/
"""

import sys
import os

# Добавляем корневую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import run_bot

if __name__ == '__main__':
    run_bot()
