/**
 * Админ-панель MineBuild - управление конфигурацией Discord-бота
 * Полностью переписанная версия с нуля
 */

class AdminPanel {
    constructor() {
        this.config = null;
        this.isLoading = false;
        this.init();
    }

    /**
     * Инициализация админ-панели
     */
    init() {
        console.log('AdminPanel: Инициализация...');
        this.setupEventListeners();
        this.loadConfiguration();
    }

    /**
     * Настройка обработчиков событий
     */
    setupEventListeners() {
        // Кнопка сохранения
        const saveBtn = document.getElementById('save-config');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveConfiguration());
        }

        // Кнопка перезагрузки
        const reloadBtn = document.getElementById('reload-config');
        if (reloadBtn) {
            reloadBtn.addEventListener('click', () => this.reloadConfiguration());
        }

        // Кнопка валидации
        const validateBtn = document.getElementById('validate-config');
        if (validateBtn) {
            validateBtn.addEventListener('click', () => this.validateConfiguration());
        }
    }

    /**
     * Загрузка конфигурации с сервера
     */
    async loadConfiguration() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showStatus('Загрузка конфигурации...', 'info');
        
        try {
            const response = await fetch('/api/config');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            this.config = await response.json();
            console.log('AdminPanel: Конфигурация загружена:', this.config);
            
            this.renderConfiguration();
            this.showStatus('Конфигурация загружена успешно', 'success');
            
        } catch (error) {
            console.error('AdminPanel: Ошибка загрузки конфигурации:', error);
            this.showStatus(`Ошибка загрузки: ${error.message}`, 'error');
            this.showLoadingError();
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Отображение конфигурации в интерфейсе
     */
    renderConfiguration() {
        if (!this.config) return;

        this.renderDiscordRoles();
        this.renderDiscordChannels();
        this.renderDonationSettings();
        this.renderSystemSettings();
    }

    /**
     * Отображение Discord ролей
     */
    renderDiscordRoles() {
        const container = document.getElementById('discord-roles');
        if (!container) return;

        const roles = this.config.discord?.roles || {};
        container.innerHTML = '';

        Object.entries(roles).forEach(([key, value]) => {
            const item = this.createConfigItem(
                `discord.roles.${key}`,
                key,
                value,
                `ID роли "${key}"`
            );
            container.appendChild(item);
        });

        if (Object.keys(roles).length === 0) {
            container.innerHTML = '<p>Нет настроенных ролей</p>';
        }
    }

    /**
     * Отображение Discord каналов
     */
    renderDiscordChannels() {
        const container = document.getElementById('discord-channels');
        if (!container) return;

        const channels = this.config.discord?.channels || {};
        container.innerHTML = '';

        Object.entries(channels).forEach(([key, value]) => {
            const item = this.createConfigItem(
                `discord.channels.${key}`,
                key,
                value,
                `ID канала "${key}"`
            );
            container.appendChild(item);
        });

        if (Object.keys(channels).length === 0) {
            container.innerHTML = '<p>Нет настроенных каналов</p>';
        }
    }

    /**
     * Отображение настроек донатов
     */
    renderDonationSettings() {
        // Состояние включения системы донатов
        const enabledContainer = document.getElementById('donations-enabled');
        if (enabledContainer) {
            enabledContainer.innerHTML = '';
            const enabled = this.config.donations?.enabled || false;
            const item = this.createConfigItem(
                'donations.enabled',
                'enabled',
                enabled,
                'Включить систему донатов',
                'checkbox'
            );
            enabledContainer.appendChild(item);
        }

        // Пороги донатов
        const thresholdsContainer = document.getElementById('donations-thresholds');
        if (thresholdsContainer) {
            thresholdsContainer.innerHTML = '';
            const thresholds = this.config.donations?.thresholds || {};
            
            Object.entries(thresholds).forEach(([key, value]) => {
                const item = this.createConfigItem(
                    `donations.thresholds.${key}`,
                    key,
                    value,
                    `Порог для "${key}" (в рублях)`,
                    'number'
                );
                thresholdsContainer.appendChild(item);
            });
        }

        // Награды
        const rewardsContainer = document.getElementById('donations-rewards');
        if (rewardsContainer) {
            rewardsContainer.innerHTML = '';
            const rewards = this.config.donations?.rewards || {};
            
            Object.entries(rewards).forEach(([key, value]) => {
                const item = this.createConfigItem(
                    `donations.rewards.${key}`,
                    key,
                    value,
                    `Включить награду "${key}"`,
                    'checkbox'
                );
                rewardsContainer.appendChild(item);
            });
        }

        // Команды Minecraft
        const commandsContainer = document.getElementById('donations-commands');
        if (commandsContainer) {
            commandsContainer.innerHTML = '';
            const commands = this.config.donations?.minecraft_commands || {};
            
            Object.entries(commands).forEach(([key, value]) => {
                const item = this.createConfigItem(
                    `donations.minecraft_commands.${key}`,
                    key,
                    value,
                    `Команда "${key}"`
                );
                commandsContainer.appendChild(item);
            });
        }
    }

    /**
     * Отображение системных настроек
     */
    renderSystemSettings() {
        const container = document.getElementById('system-settings');
        if (!container) return;

        container.innerHTML = '';

        // Таймауты
        const timeouts = this.config.system?.timeouts || {};
        Object.entries(timeouts).forEach(([key, value]) => {
            const item = this.createConfigItem(
                `system.timeouts.${key}`,
                key,
                value,
                `Таймаут "${key}" (в секундах)`,
                'number'
            );
            container.appendChild(item);
        });

        // Настройки приложений
        const application = this.config.system?.application || {};
        Object.entries(application).forEach(([key, value]) => {
            const item = this.createConfigItem(
                `system.application.${key}`,
                key,
                value,
                `Настройка приложения "${key}"`,
                'number'
            );
            container.appendChild(item);
        });
    }

    /**
     * Создание элемента конфигурации
     */
    createConfigItem(path, key, value, description, type = 'text') {
        const div = document.createElement('div');
        div.className = 'config-item';
        div.dataset.path = path;

        const label = document.createElement('label');
        label.className = 'config-label';
        label.textContent = description;
        label.setAttribute('for', path);

        const input = document.createElement('input');
        input.className = 'config-input';
        input.id = path;
        input.name = path;
        input.type = type;
        
        if (type === 'checkbox') {
            input.checked = Boolean(value);
        } else {
            input.value = value || '';
        }

        const small = document.createElement('small');
        small.className = 'config-description';
        small.textContent = `Ключ: ${key}`;

        div.appendChild(label);
        div.appendChild(input);
        div.appendChild(small);

        return div;
    }

    /**
     * Сбор данных конфигурации из формы
     */
    collectConfiguration() {
        const items = document.querySelectorAll('.config-item');
        const newConfig = JSON.parse(JSON.stringify(this.config)); // Глубокое копирование

        items.forEach(item => {
            const path = item.dataset.path;
            const input = item.querySelector('input');
            
            if (!path || !input) return;

            const pathParts = path.split('.');
            let current = newConfig;

            // Навигация по пути до предпоследнего элемента
            for (let i = 0; i < pathParts.length - 1; i++) {
                const part = pathParts[i];
                if (!(part in current)) {
                    current[part] = {};
                }
                current = current[part];
            }

            // Установка значения
            const lastKey = pathParts[pathParts.length - 1];
            if (input.type === 'checkbox') {
                current[lastKey] = input.checked;
            } else if (input.type === 'number') {
                current[lastKey] = parseFloat(input.value) || 0;
            } else {
                current[lastKey] = input.value;
            }
        });

        return newConfig;
    }

    /**
     * Сохранение конфигурации
     */
    async saveConfiguration() {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showStatus('Сохранение конфигурации...', 'info');

        try {
            const newConfig = this.collectConfiguration();
            console.log('AdminPanel: Сохранение конфигурации:', newConfig);

            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newConfig)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            this.config = newConfig;
            this.showStatus('Конфигурация сохранена успешно', 'success');

        } catch (error) {
            console.error('AdminPanel: Ошибка сохранения:', error);
            this.showStatus(`Ошибка сохранения: ${error.message}`, 'error');
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Перезагрузка конфигурации
     */
    async reloadConfiguration() {
        this.config = null;
        await this.loadConfiguration();
    }

    /**
     * Валидация конфигурации
     */
    async validateConfiguration() {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showStatus('Валидация конфигурации...', 'info');

        try {
            const currentConfig = this.collectConfiguration();
            
            // Простая валидация
            const errors = [];
            const warnings = [];

            // Проверка Discord настроек
            if (!currentConfig.discord) {
                errors.push('Отсутствует секция Discord');
            } else {
                if (!currentConfig.discord.roles || Object.keys(currentConfig.discord.roles).length === 0) {
                    warnings.push('Нет настроенных ролей Discord');
                }
                if (!currentConfig.discord.channels || Object.keys(currentConfig.discord.channels).length === 0) {
                    warnings.push('Нет настроенных каналов Discord');
                }
            }

            // Проверка настроек донатов
            if (currentConfig.donations?.enabled) {
                if (!currentConfig.donations.thresholds || Object.keys(currentConfig.donations.thresholds).length === 0) {
                    errors.push('Система донатов включена, но не настроены пороги');
                }
            }

            // Отображение результатов
            const container = document.getElementById('validation-results');
            if (container) {
                container.innerHTML = '';

                if (errors.length === 0 && warnings.length === 0) {
                    container.innerHTML = '<div class="validation-success">✅ Конфигурация валидна</div>';
                } else {
                    if (errors.length > 0) {
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'validation-errors';
                        errorDiv.innerHTML = `<strong>Ошибки:</strong><ul>${errors.map(e => `<li>${e}</li>`).join('')}</ul>`;
                        container.appendChild(errorDiv);
                    }

                    if (warnings.length > 0) {
                        const warningDiv = document.createElement('div');
                        warningDiv.className = 'validation-warnings';
                        warningDiv.innerHTML = `<strong>Предупреждения:</strong><ul>${warnings.map(w => `<li>${w}</li>`).join('')}</ul>`;
                        container.appendChild(warningDiv);
                    }
                }
            }

            if (errors.length === 0) {
                this.showStatus('Валидация прошла успешно', 'success');
            } else {
                this.showStatus(`Найдено ошибок: ${errors.length}`, 'error');
            }

        } catch (error) {
            console.error('AdminPanel: Ошибка валидации:', error);
            this.showStatus(`Ошибка валидации: ${error.message}`, 'error');
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Отображение статуса
     */
    showStatus(message, type = 'info') {
        const statusElement = document.getElementById('admin-status');
        if (!statusElement) return;

        statusElement.innerHTML = `<p class="status-${type}">${message}</p>`;
        
        // Автоматическое скрытие успешных сообщений
        if (type === 'success') {
            setTimeout(() => {
                statusElement.innerHTML = '<p>Готов к работе</p>';
            }, 3000);
        }
    }

    /**
     * Отображение ошибки загрузки
     */
    showLoadingError() {
        const containers = [
            'discord-roles',
            'discord-channels',
            'donations-enabled',
            'donations-thresholds',
            'donations-rewards',
            'donations-commands',
            'system-settings'
        ];

        containers.forEach(id => {
            const container = document.getElementById(id);
            if (container) {
                container.innerHTML = '<p class="status-error">❌ Ошибка загрузки данных</p>';
            }
        });
    }
}

// Инициализация админ-панели при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    console.log('AdminPanel: DOM загружен, создание экземпляра...');
    window.adminPanel = new AdminPanel();
});
