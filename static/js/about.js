/**
 * Слайдер для раздела "История и сюжет сервера"
 * Реализует плавное переключение между слайдами с корректной анимацией высоты
 */
document.addEventListener('DOMContentLoaded', function() {
    // Основные элементы слайдера
    const slider = document.getElementById('lore-slider');
    if (!slider) return;
    
    const slides = document.querySelectorAll('.lore-slide');
    const dots = document.querySelectorAll('.lore-dot');
    const prevBtn = document.querySelector('.lore-prev');
    const nextBtn = document.querySelector('.lore-next');
    const slidesContainer = document.querySelector('.lore-slides-container');
    
    if (!slides.length || !slidesContainer) return;
    
    // Текущий активный слайд и флаг анимации
    let currentIndex = 0;
    let isAnimating = false;
    
    // Устанавливаем начальные стили для контейнера
    slidesContainer.style.position = 'relative';
    slidesContainer.style.overflow = 'hidden';
    slidesContainer.style.transition = 'height 0.5s ease';
    
    // Устанавливаем начальные стили для слайдов
    slides.forEach((slide, index) => {
        // Базовые стили для всех слайдов
        slide.style.opacity = index === currentIndex ? '1' : '0';
        slide.style.display = index === currentIndex ? 'block' : 'none';
        
        // Если это активный слайд, устанавливаем начальную высоту контейнера
        if (index === currentIndex) {
            slidesContainer.style.height = slide.offsetHeight + 'px';
        }
    });
    
    // Обработчик для адаптации высоты при изменении размеров окна
    window.addEventListener('resize', () => {
        const activeSlide = slides[currentIndex];
        if (activeSlide) {
            slidesContainer.style.height = activeSlide.offsetHeight + 'px';
        }
    });
    
    // Функция для плавного перехода между слайдами
    function goToSlide(index) {
        if (isAnimating || index === currentIndex || index < 0 || index >= slides.length) return;
        
        isAnimating = true;
        
        // Получаем текущий и следующий слайды
        const currentSlide = slides[currentIndex];
        const nextSlide = slides[index];
        
        // 1. Подготовка следующего слайда для измерения высоты
        // Временно делаем его видимым, но прозрачным и вне потока документа
        nextSlide.style.display = 'block';
        nextSlide.style.opacity = '0';
        nextSlide.style.position = 'absolute';
        nextSlide.style.top = '0';
        nextSlide.style.left = '0';
        nextSlide.style.width = '100%';
        
        // 2. Измеряем высоту следующего слайда
        const nextHeight = nextSlide.offsetHeight;
        
        // 3. Возвращаем слайд в исходное состояние для анимации
        nextSlide.style.position = '';
        nextSlide.style.top = '';
        nextSlide.style.left = '';
        nextSlide.style.width = '';
        
        // 4. Обновляем индикаторы (точки)
        dots.forEach((dot, i) => {
            dot.classList.toggle('active', i === index);
        });
        
        // 5. Одновременно запускаем три анимации:
        // - Исчезновение текущего слайда
        currentSlide.style.transition = 'opacity 0.5s ease';
        currentSlide.style.opacity = '0';
        
        // - Изменение высоты контейнера
        slidesContainer.style.height = nextHeight + 'px';
        
        // 6. По завершении первого этапа анимации
        setTimeout(() => {
            // Скрываем предыдущий слайд
            currentSlide.style.display = 'none';
            
            // 7. Запускаем анимацию появления нового слайда
            nextSlide.style.transition = 'opacity 0.5s ease';
            nextSlide.style.opacity = '1';
            
            // 8. По завершении всех анимаций
            setTimeout(() => {
                // Сохраняем высоту контейнера!
                // НЕ сбрасываем slidesContainer.style.height
                
                // 9. Обновляем текущий индекс и флаг анимации
                currentIndex = index;
                isAnimating = false;
            }, 500);
        }, 500);
    }
    
    // Обработчики событий
    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            const prevIndex = (currentIndex - 1 + slides.length) % slides.length;
            goToSlide(prevIndex);
        });
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            const nextIndex = (currentIndex + 1) % slides.length;
            goToSlide(nextIndex);
        });
    }
    
    // Обработчики для точек навигации
    dots.forEach((dot, index) => {
        dot.addEventListener('click', () => {
            goToSlide(index);
        });
    });
    
    // Поддержка свайпов для мобильных устройств
    let touchStartX = 0;
    let touchEndX = 0;
    
    slider.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });
    
    slider.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        
        const swipeThreshold = 50;
        const swipeDistance = touchEndX - touchStartX;
        
        if (swipeDistance > swipeThreshold) {
            // Свайп вправо - предыдущий слайд
            const prevIndex = (currentIndex - 1 + slides.length) % slides.length;
            goToSlide(prevIndex);
        } else if (swipeDistance < -swipeThreshold) {
            // Свайп влево - следующий слайд
            const nextIndex = (currentIndex + 1) % slides.length;
            goToSlide(nextIndex);
        }
    }, { passive: true });
});