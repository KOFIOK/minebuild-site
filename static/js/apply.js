// Конфигурация вопросов
const formQuestions = [
    {
        id: 'nickname',
        question: 'Ваш игровой никнейм в Minecraft',
        placeholder: 'Например: Steve',
        type: 'text',
        required: true
    },
    {
        id: 'name',
        question: 'Ваше имя (реальное)',
        placeholder: 'Можете поставить прочерк, если не хотите указывать',
        type: 'text',
        required: true
    },
    {
        id: 'age',
        question: 'Ваш возраст',
        type: 'number',
        required: true
    },
    {
        id: 'experience',
        question: 'Опыт игры в Minecraft',
        type: 'radio',
        options: ['Меньше года', '1-2 года', '3-5 лет', 'Более 5 лет'],
        required: true
    },
    {
        id: 'gameplay',
        question: 'Ваш стиль игры',
        placeholder: 'Я люблю строить, но не люблю сражаться.',
        type: 'text',
        required: true
    },
    {
        id: 'important',
        question: 'Что самое важное в приватках?',
        type: 'text',
        placeholder: 'Адекватность, дружелюбность, отсутствие агрессии.',
        required: true
    },
    {
        id: 'about',
        question: 'Расскажите о себе',
        helpTexts: [
            'Пишите не только о себе в рамках игры Minecraft, но и о себе в целом: какие у вас интересы, чем занимаетесь в свободное время, какие планы на жизнь и т.д.'
        ],
        type: 'textarea',
        required: true
    }
];

class ApplicationForm {
    constructor() {
        // Проверяем, доступна ли форма заявки
        if (!document.getElementById('applicationForm')) {
            console.log('Прием заявок закрыт');
            return; // Выходим, если форма недоступна (заявки закрыты)
        }
        
        this.currentSlide = 0;
        this.answers = {};
        this.totalSlides = formQuestions.length;
        
        this.form = document.getElementById('applicationForm');
        this.slidesContainer = document.getElementById('formSlides');
        this.progressSteps = document.getElementById('progressSteps');
        this.progressLine = document.getElementById('progressLine');
        this.prevButton = document.getElementById('prevButton');
        this.nextButton = document.getElementById('nextButton');
        this.submitButton = document.getElementById('submitButton');

        this.initializeForm();
        this.bindEvents();
    }

    initializeForm() {
        // Создаем слайды и прогресс-бар
        formQuestions.forEach((question, index) => {
            this.createSlide(question, index);
            this.createProgressStep(index);
        });

        // Показываем первый слайд
        this.showSlide(0);
        this.updateProgress();
    }

    createSlide(question, index) {
        const slide = document.createElement('div');
        slide.className = 'form-slide';
        slide.dataset.slideIndex = index;

        const content = `
            <div class="question-container">
                <h2 class="question-title">
                    ${question.question}
                    ${question.required ? '<span class="required-mark">*</span>' : ''}
                </h2>
                ${this.createInputElement(question)}
            </div>
        `;

        slide.innerHTML = content;
        this.slidesContainer.appendChild(slide);
    }

    createInputElement(question) {
        let inputHtml = '';
        
        if (question.helpTexts && question.helpTexts.length > 0) {
            inputHtml += `<div class="help-texts-container">`;
            question.helpTexts.forEach((helpText, index) => {
                inputHtml += `<div class="help-text">
                    <i class="fas fa-info-circle"></i> ${helpText}
                    ${question.id === 'discord' && index === 0 ? ' (наведите для просмотра инструкции)' : ''}
                    ${question.id === 'discord' && index === 0 ? `<img src="/static/images/guide_for_discord_id.webp" alt="Как найти Discord ID" class="help-image">` : ''}
                </div>`;
            });
            inputHtml += `</div>`;
        }

        switch (question.type) {
            case 'text':
                inputHtml += `<input type="text" class="form-control" id="${question.id}" 
                    ${question.required ? 'required' : ''} 
                    ${question.placeholder ? `placeholder="${question.placeholder}"` : ''}>`;
                break;
            case 'number':
                if (question.id === 'discord') {
                    inputHtml += `<input type="text" pattern="^\\d{18,}$" class="form-control" id="${question.id}" 
                        ${question.required ? 'required' : ''} 
                        ${question.placeholder ? `placeholder="${question.placeholder}"` : ''}
                        oninput="this.value = this.value.replace(/[^0-9]/g, '')"
                        title="Discord ID должен содержать минимум 18 цифр">`;
                } else {
                    inputHtml += `<input type="number" class="form-control" id="${question.id}" 
                        ${question.required ? 'required' : ''} 
                        ${question.placeholder ? `placeholder="${question.placeholder}"` : ''}>`;
                }
                break;
            case 'textarea':
                const isAbout = question.id === 'about';
                const isBiography = question.id === 'biography';
                inputHtml += `<textarea class="form-control" id="${question.id}" rows="4" 
                    ${question.required ? 'required' : ''} 
                    ${question.placeholder ? `placeholder="${question.placeholder}"` : ''}
                    ${isAbout ? 'minlength="200"' : ''}
                    ${isBiography ? 'minlength="300" maxlength="900"' : ''}
                    ${(isAbout || isBiography) ? `oninput="updateCharacterCount(this, ${isAbout ? '200' : '300'}, ${isAbout ? '0' : '900'})"` : ''}></textarea>
                ${isAbout ? '<div class="character-count">Минимум символов: <span>0</span>/200</div>' : ''}
                ${isBiography ? '<div class="character-count">Символов: <span>0</span>/300<br>Максимум: 900</div>' : ''}`;
                break;
            case 'radio':
                inputHtml += `<div class="radio-group">`;
                question.options.forEach((option, i) => {
                    const optionId = `${question.id}_${i}`;
                    inputHtml += `
                        <div class="form-check">
                            <label for="${optionId}">
                                <input class="form-check-input" type="radio" name="${question.id}" 
                                    id="${optionId}" value="${option}" ${question.required ? 'required' : ''}>
                                ${option}
                            </label>
                        </div>`;
                });
                inputHtml += `</div>`;
                break;
        }

        return inputHtml;
    }

    createProgressStep(index) {
        const step = document.createElement('div');
        step.className = 'progress-step';
        step.dataset.step = index;
        this.progressSteps.appendChild(step);
    }

    showSlide(index) {
        const slides = this.slidesContainer.querySelectorAll('.form-slide');
        const currentSlide = this.slidesContainer.querySelector('.form-slide.active');

        // Если есть активный слайд, плавно скрываем его
        if (currentSlide) {
            currentSlide.style.opacity = '0';
            currentSlide.style.transform = 'translateX(-20px)';
            currentSlide.style.visibility = 'hidden';
            
            setTimeout(() => {
                currentSlide.classList.remove('active');
                
                // Показываем новый слайд
                const nextSlide = slides[index];
                nextSlide.classList.add('active');
                nextSlide.style.visibility = 'visible';
                
                // Принудительный reflow для запуска анимации
                nextSlide.offsetHeight;
                
                nextSlide.style.opacity = '1';
                nextSlide.style.transform = 'translateX(0)';
            }, 300);
        } else {
            // Если это первый показ
            const nextSlide = slides[index];
            nextSlide.classList.add('active');
            nextSlide.style.visibility = 'visible';
            nextSlide.style.opacity = '1';
            nextSlide.style.transform = 'translateX(0)';
        }

        // Обновляем кнопки навигации
        this.prevButton.style.display = index === 0 ? 'none' : 'flex';
        if (index === this.totalSlides - 1) {
            this.nextButton.style.display = 'none';
            this.submitButton.style.display = 'flex';
        } else {
            this.nextButton.style.display = 'flex';
            this.submitButton.style.display = 'none';
        }
    }

    updateProgress() {
        const progress = ((this.currentSlide + 1) / this.totalSlides) * 100;
        // Плавная анимация прогресс-бара
        this.progressLine.style.transition = 'width 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
        this.progressLine.style.width = `${progress}%`;

        const steps = this.progressSteps.querySelectorAll('.progress-step');
        steps.forEach((step, index) => {
            if (index <= this.currentSlide) {
                step.classList.add('active');
            } else {
                step.classList.remove('active');
            }
        });
    }

    validateCurrentSlide() {
        const currentQuestion = formQuestions[this.currentSlide];
        if (!currentQuestion.required) return true;

        const slide = this.slidesContainer.querySelector(`[data-slide-index="${this.currentSlide}"]`);
        const inputs = slide.querySelectorAll('input, textarea');
        
        if (currentQuestion.type === 'radio' || currentQuestion.type === 'checkbox') {
            const checked = slide.querySelector('input:checked');
            if (!checked) {
                this.showError(currentQuestion.question, 'Это поле обязательно для заполнения');
                return false;
            }
        } else {
            const input = inputs[0];
            if (!input.value.trim()) {
                this.showError(currentQuestion.question, 'Это поле обязательно для заполнения');
                return false;
            }

            // Обновлённая проверка Discord ID
            if (currentQuestion.id === 'discord') {
                const discordId = input.value.trim();
                if (discordId.length < 18 || !/^\d{18,}$/.test(discordId)) {
                    this.showError(currentQuestion.question, 'Discord ID должен содержать минимум 18 цифр');
                    return false;
                }
            }

            // Проверка минимальной длины для поля "О себе"
            if (currentQuestion.id === 'about' && input.value.length < 200) {
                this.showError(currentQuestion.question, `Минимальная длина текста 200 символов. Сейчас: ${input.value.length}`);
                return false;
            }

            // Проверка длины для поля "Биография"
            if (currentQuestion.id === 'biography') {
                const length = input.value.length;
                if (length < 300) {
                    this.showError(currentQuestion.question, `Минимальная длина текста 300 символов. Сейчас: ${length}`);
                    return false;
                }
                if (length > 900) {
                    this.showError(currentQuestion.question, `Максимальная длина текста 900 символов. Сейчас: ${length}`);
                    return false;
                }
            }
        }

        return true;
    }

    showError(questionText, message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        
        const currentSlide = this.slidesContainer.querySelector(`[data-slide-index="${this.currentSlide}"]`);
        const existingError = currentSlide.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }
        currentSlide.appendChild(errorDiv);
    }

    collectAnswers() {
        const answers = {};
        formQuestions.forEach(question => {
            const element = document.getElementById(question.id);
            if (element) {
                answers[question.id] = element.value;
            } else {
                // Для radio и checkbox
                const elements = document.getElementsByName(question.id);
                if (question.type === 'checkbox') {
                    answers[question.id] = Array.from(elements)
                        .filter(el => el.checked)
                        .map(el => el.value);
                } else if (question.type === 'radio') {
                    const checked = Array.from(elements).find(el => el.checked);
                    answers[question.id] = checked ? checked.value : '';
                }
            }
        });
        return answers;
    }

    bindEvents() {
        this.prevButton.addEventListener('click', () => {
            if (this.currentSlide > 0) {
                this.currentSlide--;
                this.showSlide(this.currentSlide);
                this.updateProgress();
            }
        });

        this.nextButton.addEventListener('click', () => {
            if (this.validateCurrentSlide()) {
                if (this.currentSlide < this.totalSlides - 1) {
                    this.currentSlide++;
                    this.showSlide(this.currentSlide);
                    this.updateProgress();
                }
            }
        });

        this.form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (this.validateCurrentSlide()) {
                // Получаем ссылку на кнопку отправки
                const submitButton = document.getElementById('submitButton');
                
                // Блокируем кнопку и показываем процесс загрузки
                submitButton.disabled = true;
                const originalButtonText = submitButton.innerHTML;
                submitButton.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div> Отправка...';
                
                const answers = this.collectAnswers();
                console.log('Отправка данных:', answers);
                
                try {
                    const response = await fetch('/api/submit-application', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(answers)
                    });

                    console.log('Статус ответа:', response.status);
                    const responseData = await response.json();
                    console.log('Данные ответа:', responseData);

                    if (response.ok) {
                        this.showSuccessMessage();
                    } else {
                        console.error('Ошибка сервера:', responseData);
                        this.showErrorMessage(responseData.error || 'Произошла ошибка при отправке заявки');
                        
                        // Разблокируем кнопку и восстанавливаем текст при ошибке
                        submitButton.disabled = false;
                        submitButton.innerHTML = originalButtonText;
                    }
                } catch (error) {
                    console.error('Ошибка при отправке формы:', error);
                    this.showErrorMessage('Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже.');
                    
                    // Разблокируем кнопку и восстанавливаем текст при ошибке
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalButtonText;
                }
            }
        });
    }

    showSuccessMessage() {
        // Плавно скрываем форму
        this.slidesContainer.style.opacity = '0';
        this.slidesContainer.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            this.slidesContainer.innerHTML = `
                <div class="success-message">
                    <i class="fas fa-check-circle"></i>
                    <h2>Заявка успешно отправлена!</h2>
                    <p>Ваша заявка отправлена на рассмотрение. Результат будет отправлен вам в личные сообщения Discord.</p>
                    <a href="/" class="btn btn-primary home-button">
                        <i class="fas fa-home"></i> На главную
                    </a>
                </div>
            `;
            
            requestAnimationFrame(() => {
                this.slidesContainer.style.opacity = '1';
                this.slidesContainer.style.transform = 'translateY(0)';
            });
        }, 300);

        // Скрываем кнопки навигации
        [this.prevButton, this.nextButton, this.submitButton].forEach(button => {
            button.style.opacity = '0';
            button.style.transform = 'translateY(20px)';
            setTimeout(() => {
                button.style.display = 'none';
            }, 300);
        });
    }

    showErrorMessage(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message global';
        errorDiv.textContent = message;
        this.form.insertBefore(errorDiv, this.form.firstChild);
    }
}

// Обновляем функцию подсчета символов
function updateCharacterCount(textarea, minLength, maxLength) {
    const currentLength = textarea.value.length;
    const remaining = Math.max(0, minLength - currentLength);
    const countElement = textarea.parentElement.querySelector('.character-count span');
    if (countElement) {
        countElement.textContent = currentLength;
        const countContainer = countElement.parentElement;
        
        if (maxLength > 0) {
            // Для биографии
            if (currentLength >= minLength && currentLength <= maxLength) {
                countContainer.style.color = 'var(--accent-green)';
            } else if (currentLength > maxLength) {
                countContainer.style.color = 'var(--accent-purple)';
            } else {
                countContainer.style.color = 'var(--text-secondary)';
            }
        } else {
            // Для поля "О себе"
            if (currentLength >= minLength) {
                countContainer.style.color = 'var(--accent-green)';
            } else {
                countContainer.style.color = 'var(--text-secondary)';
            }
        }
    }
}

// Инициализация формы при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    new ApplicationForm();
});