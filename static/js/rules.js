document.addEventListener('DOMContentLoaded', function() {
    // Инициализация аккордеона для правил
    initSmoothAccordion();
    
    // Активация анимаций при прокрутке
    initScrollAnimations();
    
    // Добавляем эффекты при наведении на карточки правил
    initRuleCardEffects();
});

/**
 * Инициализация аккордеона с плавной анимацией
 */
function initSmoothAccordion() {
    const accordionItems = document.querySelectorAll('.accordion-item');
    
    // Для каждого элемента аккордеона
    accordionItems.forEach(item => {
        const header = item.querySelector('.accordion-header');
        const contentWrapper = item.querySelector('.accordion-content-wrapper');
        const content = item.querySelector('.accordion-content');
        
        // Начальные установки для wrapper и content
        contentWrapper.style.height = '0px';
        
        // Обработчик клика на заголовке
        header.addEventListener('click', () => {
            // Находим активный аккордеон (если есть)
            const currentActive = document.querySelector('.accordion-item.active');
            
            // Если текущий элемент уже активен, закрываем его
            if (item.classList.contains('active')) {
                closeAccordionItem(item);
                return;
            }
            
            // Если есть другой открытый аккордеон - закрываем его
            if (currentActive) {
                closeAccordionItem(currentActive);
            }
            
            // Открываем текущий аккордеон
            openAccordionItem(item);
        });
        
        // Обработка нажатий клавиш для доступности
        header.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                header.click();
            }
        });
    });
    
    // Открываем первый аккордеон по умолчанию
    setTimeout(() => {
        if (accordionItems.length > 0) {
            openAccordionItem(accordionItems[0]);
        }
    }, 500);
    
    /**
     * Открывает элемент аккордеона с плавной анимацией
     * @param {HTMLElement} item - Элемент аккордеона
     */
    function openAccordionItem(item) {
        const contentWrapper = item.querySelector('.accordion-content-wrapper');
        const content = item.querySelector('.accordion-content');
        const header = item.querySelector('.accordion-header');
        
        // Добавляем класс active для стилей
        item.classList.add('active');
        
        // Обновляем атрибуты доступности
        header.setAttribute('aria-expanded', 'true');
        
        // Получаем высоту содержимого для анимации
        content.style.opacity = '0';
        content.style.transform = 'translateY(-10px)';
        
        // Устанавливаем высоту wrapper на основе реальной высоты content
        // Сначала делаем его временно видимым для измерения
        contentWrapper.style.height = 'auto';
        const contentHeight = contentWrapper.offsetHeight;
        contentWrapper.style.height = '0px';
        
        // Запускаем анимацию после небольшой задержки
        requestAnimationFrame(() => {
            contentWrapper.style.height = contentHeight + 'px';
            
            // После раскрытия делаем содержимое видимым
            setTimeout(() => {
                content.style.opacity = '1';
                content.style.transform = 'translateY(0)';
            }, 150);
        });
    }
    
    /**
     * Закрывает элемент аккордеона с плавной анимацией
     * @param {HTMLElement} item - Элемент аккордеона
     */
    function closeAccordionItem(item) {
        const contentWrapper = item.querySelector('.accordion-content-wrapper');
        const content = item.querySelector('.accordion-content');
        const header = item.querySelector('.accordion-header');
        
        // Получаем текущую высоту для плавной анимации закрытия
        const contentHeight = contentWrapper.offsetHeight;
        
        // Устанавливаем точную высоту перед анимацией
        contentWrapper.style.height = contentHeight + 'px';
        
        // Запускаем анимацию скрытия контента
        requestAnimationFrame(() => {
            content.style.opacity = '0';
            content.style.transform = 'translateY(-10px)';
            
            // Затем запускаем анимацию сворачивания wrapper
            setTimeout(() => {
                contentWrapper.style.height = '0px';
                
                // Убираем класс active после окончания анимации
                setTimeout(() => {
                    item.classList.remove('active');
                    header.setAttribute('aria-expanded', 'false');
                }, 300);
            }, 100);
        });
    }
}

/**
 * Инициализация анимаций при прокрутке
 */
function initScrollAnimations() {
    const animatedElements = document.querySelectorAll('.animate-slide-up, .animate-fade-in');
    
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.visibility = 'visible';
                    
                    // Активация анимации сразу после обнаружения элемента в поле зрения
                    entry.target.style.animationPlayState = 'running';
                    observer.unobserve(entry.target);
                }
            });
        }, {
            // Уменьшаем порог видимости для более раннего запуска анимации
            threshold: 0.05,
            // Увеличиваем отступ, чтобы элементы начинали анимироваться еще до появления на экране
            rootMargin: '0px 0px 10px 0px'
        });
        
        // Подготавливаем элементы для анимации
        animatedElements.forEach(element => {
            element.style.visibility = 'hidden';
            element.style.animationPlayState = 'paused';
            observer.observe(element);
        });
    } else {
        // Для браузеров без поддержки IntersectionObserver просто отображаем элементы
        animatedElements.forEach(element => {
            element.style.visibility = 'visible';
            element.style.animationPlayState = 'running';
        });
    }
}

/**
 * Добавляет эффекты наведения для карточек правил
 */
function initRuleCardEffects() {
    const ruleItems = document.querySelectorAll('.rule-item');
    
    ruleItems.forEach(item => {
        // Создаем эффект "свечения" при наведении
        item.addEventListener('mousemove', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = x / rect.width * 100;
            const centerY = y / rect.height * 100;
            
            // Применяем градиент свечения в зависимости от положения курсора
            this.style.background = 
                `radial-gradient(circle at ${centerX}% ${centerY}%, 
                    rgba(0, 229, 161, 0.15) 0%, 
                    var(--rule-item-bg) 70%)`;
        });
        
        // Сбрасываем эффект при уходе курсора
        item.addEventListener('mouseleave', function() {
            this.style.background = 'var(--rule-item-bg)';
        });
    });
}