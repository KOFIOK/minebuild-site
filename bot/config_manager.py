"""
Модуль для управления конфигурацией Discord бота MineBuild.
Поддерживает загрузку из JSON файла и обновление настроек через админ-панель.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("MineBuildBot.Config")


class BotConfig:
    """Класс для управления конфигурацией бота."""
    
    def __init__(self, config_path: str = "data/config.json"):
        """
        Инициализация конфигурации.
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        self.config_path = Path(config_path)
        self.config_data = {}
        
        # Создаем директорию data если не существует
        self.config_path.parent.mkdir(exist_ok=True)
        
        # Загружаем конфигурацию
        self._load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию по умолчанию."""
        return {
            # === DISCORD НАСТРОЙКИ ===
            "discord": {
                "guild_id": int(os.getenv('GUILD_ID', 0)),
                "roles": {
                    "moderator": 1277399739561672845,
                    "whitelist": 1150073275184074803,
                    "candidate": 1187064873847365752,
                    "donator": 1153006749218000918,
                    "minebuild_member": 1150073275184074804
                },
                "channels": {
                    "log": 1277415977549566024,
                    "candidate_chat": 1362437237513519279,
                    "donation": 1152974439311487089,
                    "application": 1360709668770418789
                }
            },
            
            # === ДОНАТЫ ===
            "donations": {
                "enabled": True,  # Глобальное включение/выключение системы донатов
                "thresholds": {
                    "thank_message": 100,      # Благодарственное сообщение
                    "role": 300,               # Роль донатера
                    "suffix": 500,             # Суффикс в игре
                    "individual_suffix": 1000  # Индивидуальный суффикс
                },
                "rewards": {
                    "thank_message_enabled": True,    # Включить благодарственное сообщение
                    "role_enabled": True,             # Включить выдачу роли донатера
                    "suffix_enabled": True,           # Включить суффикс в игре
                    "individual_suffix_enabled": True # Включить индивидуальный суффикс
                },
                "minecraft_commands": {
                    "suffix_command": "lp user {nickname} permission set title.u.donate",
                    "whitelist_add_command": "whitelist add {nickname}",
                    "whitelist_remove_command": "whitelist remove {nickname}"
                }
            },
            
            # === MINECRAFT RCON ===
            "minecraft": {
                "rcon": {
                    "timeout": 10,           # Таймаут для RCON команд (секунды)
                    "general_timeout": 15    # Общий таймаут для операций (секунды)
                }
            },
            
            # === СИСТЕМА ===
            "system": {
                "timeouts": {
                    "shutdown_normal_tasks": 5,    # Таймаут обычных задач при завершении
                    "shutdown_system_tasks": 2,    # Таймаут системных задач при завершении
                    "api_request": 10               # Таймаут API запросов
                },
                "application": {
                    "deduplication_window": 60      # Окно дедупликации заявок (секунды)
                }
            },
            
            # === СООБЩЕНИЯ И ТЕКСТЫ ===
            "messages": {
                "welcome": {
                    "title": "Добро пожаловать на MineBuild!",
                    "description": "Поздравляем! Вы были приняты на наш сервер.",
                    "color": 0x00E5A1
                },
                "donation": {
                    "title": "Новый донат!",
                    "color": 0x68caff,
                    "footer": "MineBuild Donations"
                },
                "errors": {
                    "minecraft_unavailable": "Сервер Minecraft недоступен. Пожалуйста, проверьте его состояние.",
                    "insufficient_permissions": "У вас нет прав для выполнения этой команды.",
                    "user_not_found": "Пользователь не найден.",
                    "nickname_invalid": "Некорректный никнейм Minecraft."
                }
            },
            
            # === ВАЛИДАЦИЯ ===
            "validation": {
                "minecraft_nickname": {
                    "min_length": 3,
                    "max_length": 16,
                    "pattern": "^[a-zA-Z0-9_]+$"
                }
            },
            
            # === МЕТАДАННЫЕ ===
            "_metadata": {
                "version": "1.0.0",
                "created_at": None,
                "updated_at": None,
                "updated_by": None
            }
        }
    
    def _load_config(self):
        """Загружает конфигурацию из файла или создает файл по умолчанию."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # Мерджим с дефолтным конфигом для добавления новых полей
                default_config = self._get_default_config()
                self.config_data = self._merge_configs(default_config, loaded_config)
                
                logger.info(f"✅ Конфигурация загружена из {self.config_path}")
            else:
                # Создаем файл с конфигурацией по умолчанию
                self.config_data = self._get_default_config()
                self._save_config()
                logger.info(f"📁 Создан новый файл конфигурации: {self.config_path}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке конфигурации: {e}")
            logger.info("🔄 Используется конфигурация по умолчанию")
            self.config_data = self._get_default_config()
    
    def _merge_configs(self, default: dict, loaded: dict) -> dict:
        """Рекурсивно мерджит конфигурации, добавляя новые поля из дефолтной."""
        result = default.copy()
        
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _save_config(self):
        """Сохраняет текущую конфигурацию в файл."""
        try:
            # Обновляем метаданные
            import datetime
            self.config_data["_metadata"]["updated_at"] = datetime.datetime.now().isoformat()
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Конфигурация сохранена в {self.config_path}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении конфигурации: {e}")
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Получает значение из конфигурации по пути.
        
        Args:
            path: Путь к значению, разделенный точками (например, "discord.roles.moderator")
            default: Значение по умолчанию
            
        Returns:
            Значение из конфигурации или default
        """
        try:
            keys = path.split('.')
            value = self.config_data
            
            for key in keys:
                value = value[key]
            
            return value
            
        except (KeyError, TypeError):
            return default
    
    def set(self, path: str, value: Any, save: bool = True) -> bool:
        """
        Устанавливает значение в конфигурации по пути.
        
        Args:
            path: Путь к значению, разделенный точками
            value: Новое значение
            save: Сохранить ли изменения в файл
            
        Returns:
            True если успешно, False при ошибке
        """
        try:
            keys = path.split('.')
            target = self.config_data
            
            # Навигируемся до предпоследнего ключа
            for key in keys[:-1]:
                if key not in target:
                    target[key] = {}
                target = target[key]
            
            # Устанавливаем значение
            target[keys[-1]] = value
            
            if save:
                self._save_config()
            
            logger.info(f"⚙️ Обновлена настройка {path} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при установке настройки {path}: {e}")
            return False
    
    def update_multiple(self, updates: Dict[str, Any], save: bool = True) -> bool:
        """
        Обновляет несколько настроек одновременно.
        
        Args:
            updates: Словарь путь -> значение
            save: Сохранить ли изменения в файл
            
        Returns:
            True если все обновления успешны
        """
        success = True
        
        for path, value in updates.items():
            if not self.set(path, value, save=False):
                success = False
        
        if save and success:
            self._save_config()
        
        return success
    
    def validate_discord_ids(self) -> Dict[str, bool]:
        """
        Проверяет валидность Discord ID в конфигурации.
        
        Returns:
            Словарь с результатами проверки
        """
        results = {}
        
        # Проверяем роли
        for role_name in ["moderator", "whitelist", "candidate", "donator", "minebuild_member"]:
            role_id = self.get(f"discord.roles.{role_name}")
            results[f"role_{role_name}"] = isinstance(role_id, int) and role_id > 0
        
        # Проверяем каналы
        for channel_name in ["log", "candidate_chat", "donation", "application"]:
            channel_id = self.get(f"discord.channels.{channel_name}")
            results[f"channel_{channel_name}"] = isinstance(channel_id, int) and channel_id > 0
        
        # Проверяем Guild ID
        guild_id = self.get("discord.guild_id")
        results["guild_id"] = isinstance(guild_id, int) and guild_id > 0
        
        return results
    
    def get_admin_panel_config(self) -> Dict[str, Any]:
        """
        Возвращает конфигурацию в формате для админ-панели.
        
        Returns:
            Структурированная конфигурация для отображения в админ-панели
        """
        return {
            "discord": {
                "guild_id": self.get("discord.guild_id"),
                "roles": {
                    "moderator": {
                        "id": self.get("discord.roles.moderator"),
                        "name": "Роль модератора",
                        "description": "Роль, дающая права модератора в боте"
                    },
                    "whitelist": {
                        "id": self.get("discord.roles.whitelist"),
                        "name": "Роль whitelist",
                        "description": "Роль для игроков в белом списке"
                    },
                    "candidate": {
                        "id": self.get("discord.roles.candidate"),
                        "name": "Роль кандидата",
                        "description": "Роль для кандидатов на вступление"
                    },
                    "donator": {
                        "id": self.get("discord.roles.donator"),
                        "name": "Роль донатера",
                        "description": "Роль для игроков, сделавших донат"
                    },
                    "minebuild_member": {
                        "id": self.get("discord.roles.minebuild_member"),
                        "name": "Роль Майнбилдовца",
                        "description": "Роль для одобренных участников сервера"
                    }
                },
                "channels": {
                    "log": {
                        "id": self.get("discord.channels.log"),
                        "name": "Канал логов",
                        "description": "Канал для служебных сообщений бота"
                    },
                    "candidate_chat": {
                        "id": self.get("discord.channels.candidate_chat"),
                        "name": "Чат кандидатов",
                        "description": "Канал для общения кандидатов"
                    },
                    "donation": {
                        "id": self.get("discord.channels.donation"),
                        "name": "Канал донатов",
                        "description": "Канал для уведомлений о донатах"
                    },
                    "application": {
                        "id": self.get("discord.channels.application"),
                        "name": "Канал заявок",
                        "description": "Канал для подачи заявок"
                    }
                }
            },
            "donations": {
                "enabled": {
                    "value": self.get("donations.enabled"),
                    "name": "Система донатов",
                    "description": "Глобальное включение/выключение системы донатов"
                },
                "thresholds": {
                    "thank_message": {
                        "value": self.get("donations.thresholds.thank_message"),
                        "name": "Порог благодарности",
                        "description": "Минимальная сумма для благодарственного сообщения (₽)"
                    },
                    "role": {
                        "value": self.get("donations.thresholds.role"),
                        "name": "Порог роли",
                        "description": "Минимальная сумма для получения роли донатера (₽)"
                    },
                    "suffix": {
                        "value": self.get("donations.thresholds.suffix"),
                        "name": "Порог суффикса",
                        "description": "Минимальная сумма для получения суффикса в игре (₽)"
                    },
                    "individual_suffix": {
                        "value": self.get("donations.thresholds.individual_suffix"),
                        "name": "Порог индивидуального суффикса",
                        "description": "Минимальная сумма для индивидуального суффикса (₽)"
                    }
                },
                "rewards": {
                    "thank_message": {
                        "value": self.get("donations.rewards.thank_message_enabled"),
                        "name": "Благодарственное сообщение",
                        "description": "Включить/выключить благодарственное сообщение за донат"
                    },
                    "role": {
                        "value": self.get("donations.rewards.role_enabled"),
                        "name": "Роль донатера",
                        "description": "Включить/выключить выдачу роли донатера"
                    },
                    "suffix": {
                        "value": self.get("donations.rewards.suffix_enabled"),
                        "name": "Суффикс в игре",
                        "description": "Включить/выключить выдачу суффикса в Minecraft"
                    },
                    "individual_suffix": {
                        "value": self.get("donations.rewards.individual_suffix_enabled"),
                        "name": "Индивидуальный суффикс",
                        "description": "Включить/выключить индивидуальный суффикс в игре"
                    }
                },
                "commands": {
                    "suffix": {
                        "value": self.get("donations.minecraft_commands.suffix_command"),
                        "name": "Команда суффикса",
                        "description": "Minecraft команда для выдачи суффикса донатера"
                    },
                    "whitelist_add": {
                        "value": self.get("donations.minecraft_commands.whitelist_add_command"),
                        "name": "Команда добавления в whitelist",
                        "description": "Minecraft команда для добавления игрока в whitelist"
                    },
                    "whitelist_remove": {
                        "value": self.get("donations.minecraft_commands.whitelist_remove_command"),
                        "name": "Команда удаления из whitelist",
                        "description": "Minecraft команда для удаления игрока из whitelist"
                    }
                }
            },
            "system": {
                "timeouts": {
                    "rcon": {
                        "value": self.get("minecraft.rcon.timeout"),
                        "name": "Таймаут RCON",
                        "description": "Таймаут для RCON команд (секунды)"
                    },
                    "api": {
                        "value": self.get("system.timeouts.api_request"),
                        "name": "Таймаут API",
                        "description": "Таймаут для API запросов (секунды)"
                    }
                }
            }
        }
    
    def get_simple_config(self) -> Dict[str, Any]:
        """
        Возвращает упрощенную структуру конфигурации для совместимости с JavaScript админ-панели.
        
        Returns:
            Простая структура конфигурации аналогичная config.json
        """
        return {
            "discord": {
                "guild_id": self.get("discord.guild_id"),
                "roles": {
                    "moderator": self.get("discord.roles.moderator"),
                    "whitelist": self.get("discord.roles.whitelist"),
                    "candidate": self.get("discord.roles.candidate"),
                    "donator": self.get("discord.roles.donator"),
                    "minebuild_member": self.get("discord.roles.minebuild_member")
                },
                "channels": {
                    "log": self.get("discord.channels.log"),
                    "candidate_chat": self.get("discord.channels.candidate_chat"),
                    "donation": self.get("discord.channels.donation"),
                    "application": self.get("discord.channels.application")
                }
            },
            "donations": {
                "enabled": self.get("donations.enabled"),
                "thresholds": {
                    "thank_message": self.get("donations.thresholds.thank_message"),
                    "role": self.get("donations.thresholds.role"),
                    "suffix": self.get("donations.thresholds.suffix"),
                    "individual_suffix": self.get("donations.thresholds.individual_suffix")
                },
                "rewards": {
                    "thank_message_enabled": self.get("donations.rewards.thank_message_enabled"),
                    "role_enabled": self.get("donations.rewards.role_enabled"),
                    "suffix_enabled": self.get("donations.rewards.suffix_enabled"),
                    "individual_suffix_enabled": self.get("donations.rewards.individual_suffix_enabled")
                },
                "minecraft_commands": {
                    "suffix_command": self.get("donations.minecraft_commands.suffix_command"),
                    "whitelist_add_command": self.get("donations.minecraft_commands.whitelist_add_command"),
                    "whitelist_remove_command": self.get("donations.minecraft_commands.whitelist_remove_command")
                }
            },
            "system": {
                "timeouts": {
                    "shutdown_normal_tasks": self.get("system.timeouts.shutdown_normal_tasks"),
                    "shutdown_system_tasks": self.get("system.timeouts.shutdown_system_tasks"),
                    "api_request": self.get("system.timeouts.api_request")
                },
                "application": {
                    "deduplication_window": self.get("system.application.deduplication_window")
                }
            }
        }


# Глобальный экземпляр конфигурации
_config_instance: Optional[BotConfig] = None


def get_config() -> BotConfig:
    """Получает глобальный экземпляр конфигурации."""
    global _config_instance
    if _config_instance is None:
        _config_instance = BotConfig()
    return _config_instance


def reload_config() -> BotConfig:
    """Перезагружает конфигурацию из файла."""
    global _config_instance
    _config_instance = BotConfig()
    return _config_instance


# Функции-хелперы для обратной совместимости с существующим кодом
def get_moderator_role_id() -> int:
    """Получает ID роли модератора."""
    return get_config().get("discord.roles.moderator", 0)


def get_whitelist_role_id() -> int:
    """Получает ID роли whitelist."""
    return get_config().get("discord.roles.whitelist", 0)


def get_candidate_role_id() -> int:
    """Получает ID роли кандидата."""
    return get_config().get("discord.roles.candidate", 0)


def get_donator_role_id() -> int:
    """Получает ID роли донатера."""
    return get_config().get("discord.roles.donator", 0)


def get_log_channel_id() -> int:
    """Получает ID канала логов."""
    return get_config().get("discord.channels.log", 0)


def get_donation_channel_id() -> int:
    """Получает ID канала донатов."""
    return get_config().get("discord.channels.donation", 0)


def get_application_channel_id() -> int:
    """Получает ID канала заявок."""
    return get_config().get("discord.channels.application", 0)


def get_candidate_chat_id() -> int:
    """Получает ID чата кандидатов."""
    return get_config().get("discord.channels.candidate_chat", 0)


def get_donation_thresholds() -> Dict[str, int]:
    """Получает пороги донатов."""
    config = get_config()
    return {
        "thank_message": config.get("donations.thresholds.thank_message", 100),
        "role": config.get("donations.thresholds.role", 300),
        "suffix": config.get("donations.thresholds.suffix", 500),
        "individual_suffix": config.get("donations.thresholds.individual_suffix", 1000)
    }


def get_rcon_timeout() -> int:
    """Получает таймаут для RCON команд."""
    return get_config().get("minecraft.rcon.timeout", 10)


def get_rcon_general_timeout() -> int:
    """Получает общий таймаут для RCON операций."""
    return get_config().get("minecraft.rcon.general_timeout", 15)


def get_shutdown_timeouts() -> Dict[str, int]:
    """Получает таймауты завершения работы."""
    config = get_config()
    return {
        "normal_tasks": config.get("system.timeouts.shutdown_normal_tasks", 5),
        "system_tasks": config.get("system.timeouts.shutdown_system_tasks", 2)
    }


def get_minebuild_member_role_id() -> int:
    """Получает ID роли майнбилдовца."""
    return get_config().get("discord.roles.minebuild_member", 0)


def get_minecraft_commands() -> Dict[str, str]:
    """Получает команды Minecraft."""
    config = get_config()
    return {
        "suffix": config.get("donations.minecraft_commands.suffix_command", "lp user {nickname} permission set title.u.donate"),
        "whitelist_add": config.get("donations.minecraft_commands.whitelist_add_command", "whitelist add {nickname}"),
        "whitelist_remove": config.get("donations.minecraft_commands.whitelist_remove_command", "whitelist remove {nickname}")
    }


def get_donation_rewards_config() -> Dict[str, bool]:
    """Получает настройки включения/выключения наград за донаты."""
    config = get_config()
    return {
        "thank_message": config.get("donations.rewards.thank_message_enabled", True),
        "role": config.get("donations.rewards.role_enabled", True),
        "suffix": config.get("donations.rewards.suffix_enabled", True),
        "individual_suffix": config.get("donations.rewards.individual_suffix_enabled", True)
    }


def is_donations_enabled() -> bool:
    """Проверяет, включена ли система донатов."""
    return get_config().get("donations.enabled", True)
