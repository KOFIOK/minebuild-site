/**
 * Улучшенная галерея с плавным перелистыванием без проблем с z-index
 */
class Gallery {
    constructor() {
        // Базовые элементы
        this.items = Array.from(document.querySelectorAll('.gallery-item'));
        this.dots = Array.from(document.querySelectorAll('.gallery-dot'));
        this.prevArrow = document.querySelector('.prev-arrow');
        this.nextArrow = document.querySelector('.next-arrow');
        this.track = document.querySelector('.gallery-track');
        
        // Настройки
        this.currentIndex = 0;
        this.totalItems = this.items.length;
        this.isAnimating = false;
        this.autoplayInterval = null;
        this.autoplayDelay = 5000; // 5 секунд
        this.animationDuration = 600; // 0.6 секунды
        this.mouseX = 0;
        this.isMouseDown = false;
        this.startX = 0;
        this.lastPosition = 0;
        this.allowDrag = true;
        
        if (this.totalItems <= 0) return;
        
        // Инициализация
        this.init();
    }

    /**
     * Инициализация галереи
     */
    init() {
        // Настройка начального состояния
        this.updateGallery();
        
        // Настройка обработчиков событий
        this.setupEventListeners();
        
        // Запуск автопроигрывания
        this.startAutoplay();

        // Предзагрузка изображений для плавности
        this.preloadImages();
    }

    /**
     * Настройка всех обработчиков событий
     */
    setupEventListeners() {
        // Обработчики для стрелок навигации
        if (this.prevArrow) {
            this.prevArrow.addEventListener('click', this.goToPrev.bind(this));
        }
        if (this.nextArrow) {
            this.nextArrow.addEventListener('click', this.goToNext.bind(this));
        }

        // Обработчики для точек навигации
        this.dots.forEach((dot, index) => {
            dot.addEventListener('click', () => this.goToSlide(index));
        });

        // Обработчики для боковых слайдов
        this.items.forEach((item) => {
            item.addEventListener('click', (e) => {
                const index = parseInt(item.dataset.index);
                if (index === this.currentIndex) return;
                
                if (item.classList.contains('prev') || item.classList.contains('prev-2')) {
                    this.goToPrev();
                } else if (item.classList.contains('next') || item.classList.contains('next-2')) {
                    this.goToNext();
                }
            });
        });

        // Клавиатурная навигация
        document.addEventListener('keydown', (e) => {
            if (this.isWithinViewport(this.track)) {
                if (e.key === 'ArrowLeft') {
                    this.goToPrev();
                } else if (e.key === 'ArrowRight') {
                    this.goToNext();
                }
            }
        });

        // Поддержка свайпов на мобильных устройствах
        let gallerySection = document.querySelector('.gallery-section');
        if (gallerySection) {
            gallerySection.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
            gallerySection.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: true });
            gallerySection.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });
            
            // Поддержка перетаскивания на ПК
            gallerySection.addEventListener('mousedown', this.handleMouseDown.bind(this));
            document.addEventListener('mousemove', this.handleMouseMove.bind(this));
            document.addEventListener('mouseup', this.handleMouseUp.bind(this));
        }

        // Перезапуск автопроигрывания при возвращении на вкладку
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                this.startAutoplay();
            } else {
                this.stopAutoplay();
            }
        });
    }

    /**
     * Предзагрузка изображений для плавной работы
     */
    preloadImages() {
        this.items.forEach(item => {
            const img = item.querySelector('img');
            if (img) {
                const src = img.getAttribute('src');
                if (src) {
                    const image = new Image();
                    image.src = src;
                }
            }
        });
    }

    /**
     * Проверяет, находится ли элемент в видимой части экрана
     * @param {Element} element - Элемент для проверки
     * @return {Boolean} - Результат проверки
     */
    isWithinViewport(element) {
        if (!element) return false;
        
        const rect = element.getBoundingClientRect();
        return (
            rect.top < (window.innerHeight || document.documentElement.clientHeight) &&
            rect.bottom > 0 &&
            rect.left < (window.innerWidth || document.documentElement.clientWidth) &&
            rect.right > 0
        );
    }

    /**
     * Обновление состояния галереи
     */
    updateGallery() {
        if (!this.track) return;
        
        // Удаляем все классы позиционирования
        this.items.forEach(item => {
            item.classList.remove('active', 'prev', 'next', 'prev-2', 'next-2');
        });
        
        // Обновляем индикаторы
        this.dots.forEach((dot, index) => {
            dot.classList.toggle('active', index === this.currentIndex);
        });
        
        // Получаем индексы для видимых слайдов
        const prevIndex2 = (this.currentIndex - 2 + this.totalItems) % this.totalItems;
        const prevIndex = (this.currentIndex - 1 + this.totalItems) % this.totalItems;
        const nextIndex = (this.currentIndex + 1) % this.totalItems;
        const nextIndex2 = (this.currentIndex + 2) % this.totalItems;
        
        // Добавляем классы позиционирования
        this.items[this.currentIndex].classList.add('active');
        this.items[prevIndex].classList.add('prev');
        this.items[nextIndex].classList.add('next');
        this.items[prevIndex2].classList.add('prev-2');
        this.items[nextIndex2].classList.add('next-2');
    }

    /**
     * Переход к предыдущему слайду
     */
    goToPrev() {
        if (this.isAnimating) return;
        
        this.isAnimating = true;
        this.currentIndex = (this.currentIndex - 1 + this.totalItems) % this.totalItems;
        
        this.updateGallery();
        this.resetAutoplay();
        
        setTimeout(() => {
            this.isAnimating = false;
        }, this.animationDuration);
    }

    /**
     * Переход к следующему слайду
     */
    goToNext() {
        if (this.isAnimating) return;
        
        this.isAnimating = true;
        this.currentIndex = (this.currentIndex + 1) % this.totalItems;
        
        this.updateGallery();
        this.resetAutoplay();
        
        setTimeout(() => {
            this.isAnimating = false;
        }, this.animationDuration);
    }

    /**
     * Переход к определённому слайду
     * @param {Number} index - Индекс слайда
     */
    goToSlide(index) {
        if (this.isAnimating || index === this.currentIndex || index < 0 || index >= this.totalItems) return;
        
        this.isAnimating = true;
        this.currentIndex = index;
        
        this.updateGallery();
        this.resetAutoplay();
        
        setTimeout(() => {
            this.isAnimating = false;
        }, this.animationDuration);
    }

    /**
     * Запуск автопроигрывания
     */
    startAutoplay() {
        this.stopAutoplay();
        
        this.autoplayInterval = setInterval(() => {
            if (!document.hidden && this.isWithinViewport(this.track)) {
                this.goToNext();
            }
        }, this.autoplayDelay);
    }

    /**
     * Остановка автопроигрывания
     */
    stopAutoplay() {
        if (this.autoplayInterval) {
            clearInterval(this.autoplayInterval);
            this.autoplayInterval = null;
        }
    }

    /**
     * Перезапуск автопроигрывания
     */
    resetAutoplay() {
        this.stopAutoplay();
        this.startAutoplay();
    }

    /**
     * Обработка начала касания (мобильные устройства)
     * @param {TouchEvent} e - Событие касания
     */
    handleTouchStart(e) {
        if (this.isAnimating) return;
        
        this.startX = e.touches[0].clientX;
        this.lastPosition = this.startX;
        this.allowDrag = true;
    }

    /**
     * Обработка движения пальца (мобильные устройства)
     * @param {TouchEvent} e - Событие касания
     */
    handleTouchMove(e) {
        if (!this.allowDrag) return;
        
        const currentX = e.touches[0].clientX;
        const diff = currentX - this.lastPosition;
        this.lastPosition = currentX;
    }

    /**
     * Обработка окончания касания (мобильные устройства)
     * @param {TouchEvent} e - Событие касания
     */
    handleTouchEnd(e) {
        if (!this.allowDrag) return;
        
        const diff = this.lastPosition - this.startX;
        
        if (Math.abs(diff) > 50) {
            if (diff > 0) {
                this.goToPrev();
            } else {
                this.goToNext();
            }
        }
        
        this.allowDrag = false;
    }

    /**
     * Обработка нажатия мыши (ПК)
     * @param {MouseEvent} e - Событие мыши
     */
    handleMouseDown(e) {
        if (this.isAnimating) return;
        
        this.isMouseDown = true;
        this.startX = e.clientX;
        this.lastPosition = this.startX;
        this.allowDrag = true;
        
        e.preventDefault(); // Предотвращаем выделение текста
    }

    /**
     * Обработка движения мыши (ПК)
     * @param {MouseEvent} e - Событие мыши
     */
    handleMouseMove(e) {
        if (!this.isMouseDown || !this.allowDrag) return;
        
        const currentX = e.clientX;
        const diff = currentX - this.lastPosition;
        this.lastPosition = currentX;
    }

    /**
     * Обработка отпускания кнопки мыши (ПК)
     * @param {MouseEvent} e - Событие мыши
     */
    handleMouseUp(e) {
        if (!this.isMouseDown || !this.allowDrag) return;
        
        this.isMouseDown = false;
        const diff = this.lastPosition - this.startX;
        
        if (Math.abs(diff) > 50) {
            if (diff > 0) {
                this.goToPrev();
            } else {
                this.goToNext();
            }
        }
        
        this.allowDrag = false;
    }
}

// Инициализация галереи после загрузки страницы
document.addEventListener('DOMContentLoaded', () => {
    const gallery = new Gallery();
    
    // Инициализация функционала для таблицы модификаций
    initModsTable();
});

/**
 * Инициализация и управление таблицей модификаций
 */
function initModsTable() {
    const modsTable = document.querySelector('.mods-table');
    if (!modsTable) return;
    
    const modsTableBody = modsTable.querySelector('tbody');
    const searchInput = document.querySelector('.mods-search-input');
    const filterButtons = document.querySelectorAll('.filter-button');
    const sortableHeaders = document.querySelectorAll('.mods-table th.sortable');
    const showingInfo = document.querySelector('.showing-info');
    
    let modRows = Array.from(modsTableBody.querySelectorAll('tr'));
    let currentFilter = 'all';
    let currentSort = { column: 'name', direction: 'asc' };
    let searchTerm = '';
    
    /**
     * Применение фильтров и сортировки к таблице
     */
    function updateTable() {
        const filteredRows = modRows.filter(row => {
            // Фильтрация по категории
            if (currentFilter !== 'all' && row.dataset.category !== currentFilter) {
                return false;
            }
            
            // Фильтрация по поисковому запросу
            if (searchTerm) {
                const searchLower = searchTerm.toLowerCase();
                const nameText = row.querySelector('.mod-name').textContent.toLowerCase();
                const descText = row.querySelector('.mod-description').textContent.toLowerCase();
                return nameText.includes(searchLower) || descText.includes(searchLower);
            }
            
            return true;
        });
        
        // Сортировка отфильтрованных строк
        filteredRows.sort((a, b) => {
            let valueA, valueB;
            
            if (currentSort.column === 'name') {
                valueA = a.querySelector('.mod-name').textContent.toLowerCase();
                valueB = b.querySelector('.mod-name').textContent.toLowerCase();
            } else if (currentSort.column === 'category') {
                valueA = a.dataset.category;
                valueB = b.dataset.category;
            }
            
            if (valueA < valueB) return currentSort.direction === 'asc' ? -1 : 1;
            if (valueA > valueB) return currentSort.direction === 'asc' ? 1 : -1;
            return 0;
        });
        
        // Очистка таблицы
        modsTableBody.innerHTML = '';
        
        // Добавление отсортированных и отфильтрованных строк
        filteredRows.forEach(row => {
            modsTableBody.appendChild(row);
        });
        
        // Обновление информации о количестве отображаемых модов
        if (showingInfo) {
            showingInfo.textContent = `Показано ${filteredRows.length} из ${modRows.length} модификаций`;
        }
    }
    
    // Обработка поискового запроса
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchTerm = e.target.value.trim();
            updateTable();
        });
    }
    
    // Обработка фильтров по категориям
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            currentFilter = button.dataset.filter;
            updateTable();
        });
    });
    
    // Обработка сортировки по столбцам
    sortableHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            
            if (currentSort.column === column) {
                // Меняем направление сортировки, если это тот же столбец
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                // Сбрасываем сортировку для всех столбцов
                sortableHeaders.forEach(h => {
                    h.classList.remove('sort-asc', 'sort-desc');
                });
                
                // Устанавливаем новый столбец для сортировки
                currentSort.column = column;
                currentSort.direction = 'asc';
            }
            
            // Обновляем визуальное представление сортировки
            header.classList.remove('sort-asc', 'sort-desc');
            header.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
            
            updateTable();
        });
    });
    
    // Инициализация с изначальными настройками
    updateTable();
}