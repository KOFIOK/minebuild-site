class Gallery {
    constructor() {
        this.items = document.querySelectorAll('.gallery-item');
        this.dots = document.querySelectorAll('.gallery-dot');
        this.currentIndex = 0;
        this.totalItems = this.items.length;
        this.isAnimating = false;
        this.autoplayInterval = null;
        this.autoplayDelay = 5000;

        this.init();
    }

    init() {
        // Инициализация обработчиков событий для точек
        this.dots.forEach((dot, index) => {
            dot.addEventListener('click', () => this.goToSlide(index));
        });

        // Добавляем обработчики для боковых изображений
        this.items.forEach(item => {
            item.addEventListener('click', (e) => {
                if (!this.isAnimating) {
                    if (item.classList.contains('prev')) {
                        e.preventDefault();
                        this.prevSlide();
                    } else if (item.classList.contains('next')) {
                        e.preventDefault();
                        this.nextSlide();
                    }
                }
            });
        });

        // Предзагрузка изображений
        this.preloadImages();

        // Запуск автопроигрывания
        this.startAutoplay();

        // Первоначальное отображение
        this.updateSlides();
    }

    preloadImages() {
        this.items.forEach(item => {
            const img = item.querySelector('img');
            if (img) {
                const src = img.getAttribute('src');
                const image = new Image();
                image.src = src;
                image.onload = () => {
                    img.classList.add('loaded');
                };
            }
        });
    }

    updateSlides() {
        // Сначала скрываем все слайды
        this.items.forEach(item => {
            item.classList.remove('prev', 'current', 'next', 'visible');
            item.classList.add('hidden');
        });

        // Вычисляем индексы для соседних слайдов
        const prevIndex = (this.currentIndex - 1 + this.totalItems) % this.totalItems;
        const nextIndex = (this.currentIndex + 1) % this.totalItems;

        // Устанавливаем классы для видимых слайдов
        this.items[prevIndex].classList.remove('hidden');
        this.items[prevIndex].classList.add('prev');

        this.items[this.currentIndex].classList.remove('hidden');
        this.items[this.currentIndex].classList.add('current');

        this.items[nextIndex].classList.remove('hidden');
        this.items[nextIndex].classList.add('next');

        // Добавляем небольшую задержку для появления следующего слайда
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                this.items[nextIndex].classList.add('visible');
            });
        });

        // Обновляем точки навигации
        this.dots.forEach((dot, index) => {
            dot.classList.toggle('active', index === this.currentIndex);
        });

        // Устанавливаем флаг анимации
        this.isAnimating = true;
        setTimeout(() => {
            this.isAnimating = false;
        }, 600);
    }

    prevSlide() {
        if (!this.isAnimating) {
            this.currentIndex = (this.currentIndex - 1 + this.totalItems) % this.totalItems;
            this.updateSlides();
            this.resetAutoplay();
        }
    }

    nextSlide() {
        if (!this.isAnimating) {
            this.currentIndex = (this.currentIndex + 1) % this.totalItems;
            this.updateSlides();
            this.resetAutoplay();
        }
    }

    goToSlide(index) {
        if (!this.isAnimating && index !== this.currentIndex) {
            this.currentIndex = index;
            this.updateSlides();
            this.resetAutoplay();
        }
    }

    startAutoplay() {
        if (this.autoplayInterval) {
            clearInterval(this.autoplayInterval);
        }
        this.autoplayInterval = setInterval(() => this.nextSlide(), this.autoplayDelay);
    }

    resetAutoplay() {
        this.startAutoplay();
    }
}

// Инициализация галереи после загрузки DOM
document.addEventListener('DOMContentLoaded', () => {
    new Gallery();
});