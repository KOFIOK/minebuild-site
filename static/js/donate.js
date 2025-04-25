// Обработка платежной формы MineBuild
document.addEventListener('DOMContentLoaded', function() {
    const paymentForm = document.querySelector('.payment-form');
    
    if (paymentForm) {
        const nicknameInput = document.getElementById('payment-comment');
        const amountInput = document.getElementById('payment-amount');

        // Добавляем валидацию полей в реальном времени
        if (nicknameInput) {
            // Создаем контейнер для сообщения валидации никнейма
            const nicknameGroup = nicknameInput.closest('.payment-input-group');
            const validationMessage = document.createElement('div');
            validationMessage.className = 'validation-message';
            validationMessage.textContent = 'Пожалуйста, укажите ваш игровой ник';
            nicknameGroup.appendChild(validationMessage);

            // Добавляем информационное сообщение
            const nicknameInfo = document.createElement('div');
            nicknameInfo.className = 'nickname-info';
            nicknameInfo.innerHTML = '<i class="fas fa-info-circle"></i> Обязательно для получения наград';
            nicknameGroup.appendChild(nicknameInfo);

            // Валидация при потере фокуса
            nicknameInput.addEventListener('blur', function() {
                if (!this.value.trim()) {
                    this.classList.add('input-error');
                    validationMessage.classList.add('show');
                } else {
                    this.classList.remove('input-error');
                    validationMessage.classList.remove('show');
                }
            });

            // Снимаем ошибку при вводе
            nicknameInput.addEventListener('input', function() {
                if (this.value.trim()) {
                    this.classList.remove('input-error');
                    validationMessage.classList.remove('show');
                }
            });
        }

        // Валидация суммы
        if (amountInput) {
            const amountGroup = amountInput.closest('.payment-input-group');
            const amountValidation = document.createElement('div');
            amountValidation.className = 'validation-message';
            amountValidation.textContent = 'Минимальная сумма пожертвования - 100 ₽';
            amountGroup.appendChild(amountValidation);

            amountInput.addEventListener('blur', function() {
                const value = parseInt(this.value, 10);
                if (isNaN(value) || value < 100) {
                    this.classList.add('input-error');
                    amountValidation.classList.add('show');
                    this.value = Math.max(100, value || 100);
                } else {
                    this.classList.remove('input-error');
                    amountValidation.classList.remove('show');
                }
            });

            amountInput.addEventListener('input', function() {
                const value = parseInt(this.value, 10);
                if (!isNaN(value) && value >= 100) {
                    this.classList.remove('input-error');
                    amountValidation.classList.remove('show');
                }
            });
        }

        // Метод для прямой отправки формы на ЮMoney
        paymentForm.addEventListener('submit', function(event) {
            const nickname = document.getElementById('payment-comment');
            const amount = document.getElementById('payment-amount');
            
            // Проверка данных
            if (!amount.value || amount.value < 100) {
                event.preventDefault();
                showMessage('Минимальная сумма пожертвования - 100 ₽', 'error');
                amount.classList.add('input-error');
                return false;
            }
            
            if (!nickname.value.trim()) {
                event.preventDefault();
                showMessage('Пожалуйста, укажите игровой ник', 'error');
                nickname.classList.add('input-error');
                return false;
            }
            
            // Если всё правильно, форма отправится обычным способом
            return true;
        });
        
        // Предварительный выбор суммы
        const rewardOptions = document.querySelectorAll('.reward-option');
        rewardOptions.forEach(option => {
            option.addEventListener('click', function() {
                const amountText = this.querySelector('.reward-amount').textContent;
                const amount = parseInt(amountText.replace(/\D/g, ''));
                document.getElementById('payment-amount').value = amount;
                // Сбрасываем ошибку при выборе суммы
                document.getElementById('payment-amount').classList.remove('input-error');
                const amountValidation = document.querySelector('#payment-amount').closest('.payment-input-group').querySelector('.validation-message');
                if (amountValidation) {
                    amountValidation.classList.remove('show');
                }
            });
        });
    }
});

// Функция для отображения сообщений пользователю
function showMessage(message, type = 'info') {
    // Проверяем, есть ли уже сообщение на странице
    let messageContainer = document.querySelector('.donation-message');
    
    if (!messageContainer) {
        // Если контейнера нет, создаем его
        messageContainer = document.createElement('div');
        messageContainer.className = 'donation-message';
        const formContainer = document.querySelector('.yoomoney-form-container');
        formContainer.parentNode.insertBefore(messageContainer, formContainer);
    }
    
    // Настраиваем класс в зависимости от типа сообщения
    messageContainer.className = `donation-message ${type}`;
    messageContainer.textContent = message;
    
    // Автоматически скрываем через 5 секунд
    setTimeout(() => {
        messageContainer.classList.add('fade-out');
        setTimeout(() => {
            messageContainer.remove();
        }, 500);
    }, 5000);
}