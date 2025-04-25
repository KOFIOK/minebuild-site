// Обработка плавного скролла для кнопки "Перейти к пожертвованию"
document.addEventListener('DOMContentLoaded', function() {
    const scrollBtn = document.querySelector('.donate-scroll-btn');
    if (scrollBtn) {
        scrollBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                // Плавная прокрутка к элементу
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                // Добавление эффекта подсветки секции после прокрутки
                setTimeout(() => {
                    targetElement.classList.add('highlight-section');
                    
                    // Убираем класс подсветки через 1.5 секунды
                    setTimeout(() => {
                        targetElement.classList.remove('highlight-section');
                    }, 1500);
                }, 500);
            }
        });
    }

    // Функция для отображения сообщений пользователю
    function showMessage(message, type = 'info') {
        const messagesContainer = document.querySelector('.yoomoney-form-container');
        if (!messagesContainer) return;
        
        const messageElement = document.createElement('div');
        messageElement.className = `donation-message ${type}`;
        messageElement.innerHTML = `<i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i> <span>${message}</span>`;
        
        messagesContainer.insertBefore(messageElement, messagesContainer.firstChild);
        
        // Удаляем сообщение через 5 секунд
        setTimeout(() => {
            messageElement.classList.add('fade-out');
            setTimeout(() => {
                messageElement.remove();
            }, 500);
        }, 5000);
    }
    
    // Обработка платежной формы MineBuild
    console.log("DOM загружен, инициализация скрипта donate.js");
    const paymentForm = document.querySelector('.payment-form');
    
    if (paymentForm) {
        console.log("Форма оплаты найдена, настраиваем обработчики");
        const nicknameInput = document.getElementById('payment-comment');
        const amountInput = document.getElementById('payment-amount');
        const submitButton = paymentForm.querySelector('.payment-submit-btn');
        
        console.log("Найдены элементы формы:", {
            nicknameInput: !!nicknameInput,
            amountInput: !!amountInput,
            submitButton: !!submitButton
        });

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

        // Метод для отправки формы на ЮMoney через API сервера
        paymentForm.addEventListener('submit', function(event) {
            console.log("Событие отправки формы сработало!");
            event.preventDefault(); // Останавливаем стандартную отправку формы
            
            const nickname = document.getElementById('payment-comment').value;
            const amount = document.getElementById('payment-amount').value;
            
            // Используем банковскую карту как способ оплаты по умолчанию 
            const paymentType = 'AC'; // AC - банковская карта
            
            console.log("Собраны данные формы:", { nickname, amount, paymentType });
            
            // Проверка данных
            if (!amount || amount < 100) {
                console.log("Ошибка: некорректная сумма", amount);
                showMessage('Минимальная сумма пожертвования - 100 ₽', 'error');
                document.getElementById('payment-amount').classList.add('input-error');
                return false;
            }
            
            if (!nickname || !nickname.trim()) {
                console.log("Ошибка: никнейм не указан");
                showMessage('Пожалуйста, укажите игровой ник', 'error');
                document.getElementById('payment-comment').classList.add('input-error');
                return false;
            }
            
            // Показываем индикатор загрузки
            console.log("Отправляем запрос на создание платежа");
            showMessage('Подготовка платежа...', 'info');
            
            // Отправляем запрос на сервер для получения защищенного URL и токена
            fetch('/api/create-payment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    amount: amount,
                    comment: nickname,
                    payment_type: paymentType
                }),
            })
            .then(response => {
                console.log("Получен ответ сервера:", response.status);
                return response.json();
            })
            .then(data => {
                console.log("Получены данные платежа:", data);
                if (data.success) {
                    // Сохраняем данные в localStorage для восстановления при необходимости
                    localStorage.setItem('donation_nickname', nickname);
                    localStorage.setItem('donation_amount', amount);
                    localStorage.setItem('donation_token', data.donation_token);
                    
                    // Перенаправляем на страницу оплаты
                    console.log("Перенаправляем на URL:", data.redirect_url);
                    showMessage('Перенаправляем вас на страницу оплаты...', 'info');
                    setTimeout(() => {
                        window.location.href = data.redirect_url;
                    }, 1000);
                } else {
                    console.error("Ошибка при создании платежа:", data.error);
                    showMessage(data.error || 'Произошла ошибка при создании платежа', 'error');
                }
            })
            .catch(error => {
                console.error('Ошибка API запроса:', error);
                showMessage('Произошла ошибка при подготовке платежа. Пожалуйста, попробуйте еще раз.', 'error');
            });
            
            return false;
        });
        
        // Для дополнительной надежности добавим прямой обработчик клика на кнопку
        if (submitButton) {
            submitButton.addEventListener('click', function(e) {
                console.log("Клик по кнопке отправки формы");
                // Проверим, сработает ли событие submit формы или нужен дополнительный триггер
                if (!paymentForm.checkValidity()) {
                    paymentForm.reportValidity(); // Показать стандартные сообщения валидации
                }
            });
        }
        
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
    } else {
        console.error("Форма оплаты не найдена на странице!");
    }
});