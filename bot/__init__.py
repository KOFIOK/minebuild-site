"""
MineBuild Discord Bot

Модульная структуря Discord бота для сервера MineBuild.
"""

__version__ = "2.0.0"
__author__ = "MineBuild Team"

from .main import MineBuildBot, run_bot

__all__ = ["MineBuildBot", "run_bot"]
