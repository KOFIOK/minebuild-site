// Админ-панель JavaScript

// Загрузка конфигурации при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    loadConfiguration();
});

// Загрузка конфигурации
async function loadConfiguration() {
    try {
        showStatus('Загрузка конфигурации...', 'info');
        
        const response = await fetch('/api/config');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            populateConfigForm(data.config);
            if (data.config.validation) {
                displayValidationResults(data.config.validation);
            }
            showStatus('Конфигурация загружена', 'success');
        } else {
            showStatus('Ошибка при загрузке конфигурации: ' + (data.error || 'Неизвестная ошибка'), 'error');
        }
    } catch (error) {
        console.error('Ошибка загрузки конфигурации:', error);
        showStatus('Ошибка при загрузке конфигурации: ' + error.message, 'error');
    }
}

// Заполнение формы конфигурации
function populateConfigForm(config) {
    if (!config) {
        console.error('Конфигурация не получена');
        return;
    }

    // Discord роли
    const rolesContainer = document.getElementById('discord-roles');
    if (rolesContainer && config.discord && config.discord.roles) {
        rolesContainer.innerHTML = '';
        for (const [key, role] of Object.entries(config.discord.roles)) {
            rolesContainer.appendChild(createConfigItem(
                `discord.roles.${key}`,
                role.name || key,
                role.description || '',
                role.id || '',
                'number'
            ));
        }
    }
    
    // Discord каналы
    const channelsContainer = document.getElementById('discord-channels');
    if (channelsContainer && config.discord && config.discord.channels) {
        channelsContainer.innerHTML = '';
        for (const [key, channel] of Object.entries(config.discord.channels)) {
            channelsContainer.appendChild(createConfigItem(
                `discord.channels.${key}`,
                channel.name,
                channel.description,
                channel.id,
                'number'
            ));
        }
    }
    
    // Настройки донатов
    const enabledContainer = document.getElementById('donations-enabled');
    if (enabledContainer && config.donations && config.donations.enabled) {
        enabledContainer.innerHTML = '';
        enabledContainer.appendChild(createConfigItem(
            'donations.enabled',
            config.donations.enabled.name,
            config.donations.enabled.description,
            config.donations.enabled.value,
            'checkbox'
        ));
    }
    
    // Пороги донатов
    const thresholdsContainer = document.getElementById('donations-thresholds');
    if (thresholdsContainer && config.donations && config.donations.thresholds) {
        thresholdsContainer.innerHTML = '';
        for (const [key, threshold] of Object.entries(config.donations.thresholds)) {
            thresholdsContainer.appendChild(createConfigItem(
                `donations.thresholds.${key}`,
                threshold.name,
                threshold.description,
                threshold.value,
                'number'
            ));
        }
    }
    
    // Награды донатов
    const rewardsContainer = document.getElementById('donations-rewards');
    if (rewardsContainer && config.donations && config.donations.rewards) {
        rewardsContainer.innerHTML = '';
        for (const [key, reward] of Object.entries(config.donations.rewards)) {
            rewardsContainer.appendChild(createConfigItem(
                `donations.rewards.${key}`,
                reward.name,
                reward.description,
                reward.value,
                'checkbox'
            ));
        }
    }
    
    // Команды Minecraft
    const commandsContainer = document.getElementById('donations-commands');
    if (commandsContainer && config.donations && config.donations.commands) {
        commandsContainer.innerHTML = '';
        for (const [key, command] of Object.entries(config.donations.commands)) {
            commandsContainer.appendChild(createConfigItem(
                `donations.minecraft_commands.${key}`,
                command.name,
                command.description,
                command.value,
                'text'
            ));
        }
    }
    
    // Системные таймауты
    const timeoutsContainer = document.getElementById('system-timeouts');
    if (timeoutsContainer && config.system && config.system.timeouts) {
        timeoutsContainer.innerHTML = '';
        for (const [key, timeout] of Object.entries(config.system.timeouts)) {
            timeoutsContainer.appendChild(createConfigItem(
                `system.timeouts.${key}`,
                timeout.name,
                timeout.description,
                timeout.value,
                'number'
            ));
        }
    }
}

// Создание элемента конфигурации
function createConfigItem(path, name, description, value, type) {
    const item = document.createElement('div');
    item.className = 'config-item';
    
    const label = document.createElement('label');
    label.textContent = name;
    label.className = 'config-label';
    
    const input = document.createElement('input');
    input.type = type === 'checkbox' ? 'checkbox' : (type === 'number' ? 'number' : 'text');
    input.className = 'config-input';
    input.dataset.path = path;
    
    if (type === 'checkbox') {
        input.checked = value;
    } else {
        input.value = value;
    }
    
    const desc = document.createElement('small');
    desc.textContent = description;
    desc.className = 'config-description';
    
    item.appendChild(label);
    item.appendChild(input);
    item.appendChild(desc);
    
    return item;
}

// Отображение результатов валидации
function displayValidationResults(validation) {
    const container = document.getElementById('validation-results');
    if (!container || !validation) return;
    
    container.innerHTML = '';
    
    for (const [key, isValid] of Object.entries(validation)) {
        const item = document.createElement('div');
        item.className = `validation-item ${isValid ? 'valid' : 'invalid'}`;
        item.innerHTML = `
            <span class="validation-icon">${isValid ? '✅' : '❌'}</span>
            <span class="validation-text">${key}</span>
        `;
        container.appendChild(item);
    }
}

// Сохранение конфигурации
async function saveConfiguration() {
    try {
        showStatus('Сохранение конфигурации...', 'info');
        
        const updates = {};
        const inputs = document.querySelectorAll('.config-input');
        
        inputs.forEach(input => {
            const path = input.dataset.path;
            let value = input.type === 'checkbox' ? input.checked : input.value;
            
            // Преобразуем числовые значения
            if (input.type === 'number') {
                value = parseInt(value) || 0;
            }
            
            updates[path] = value;
        });
        
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({updates})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatus(`Конфигурация сохранена (${data.updated_count} изменений)`, 'success');
            // Перезагружаем конфигурацию для отображения актуальных данных
            setTimeout(loadConfiguration, 1000);
        } else {
            showStatus('Ошибка при сохранении: ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('Ошибка при сохранении: ' + error.message, 'error');
    }
}

// Перезагрузка конфигурации
async function reloadConfiguration() {
    try {
        showStatus('Перезагрузка конфигурации...', 'info');
        
        const response = await fetch('/api/config/reload', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatus('Конфигурация перезагружена', 'success');
            // Перезагружаем данные на странице
            setTimeout(loadConfiguration, 1000);
        } else {
            showStatus('Ошибка при перезагрузке: ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('Ошибка при перезагрузке: ' + error.message, 'error');
    }
}

// Валидация конфигурации
async function validateConfiguration() {
    try {
        showStatus('Проверка конфигурации...', 'info');
        
        const response = await fetch('/api/config/validate');
        const data = await response.json();
        
        if (data.success) {
            displayValidationResults(data.validation);
            const summary = data.summary;
            showStatus(`Валидация завершена: ${summary.valid_count}/${summary.total_count} корректных настроек`, 
                      summary.is_valid ? 'success' : 'warning');
        } else {
            showStatus('Ошибка при валидации: ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('Ошибка при валидации: ' + error.message, 'error');
    }
}

// Отображение статуса операций
function showStatus(message, type) {
    const statusDiv = document.getElementById('admin-status');
    if (!statusDiv) return;
    
    statusDiv.innerHTML = `<div class="status-message status-${type}">${message}</div>`;
    
    // Автоматически скрываем сообщение через 5 секунд
    setTimeout(() => {
        if (statusDiv) {
            statusDiv.innerHTML = '';
        }
    }, 5000);
}
