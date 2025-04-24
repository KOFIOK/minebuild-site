document.addEventListener('DOMContentLoaded', function() {
    
    // Инициализация слайдера для секции лора
    function initLoreSlider() {
        const loreSlider = document.querySelector('.lore-slider');
        if (!loreSlider) return;
        
        const slidesContainer = loreSlider.querySelector('.lore-slides-container');
        const slides = loreSlider.querySelectorAll('.lore-slide');
        const prevArrow = loreSlider.querySelector('.lore-prev');
        const nextArrow = loreSlider.querySelector('.lore-next');
        const dots = loreSlider.querySelectorAll('.lore-dot');
        
        let currentSlide = 0;
        let isAnimating = false;
        
        // Установка начальной высоты контейнера
        function updateContainerHeight(slideIndex) {
            const slide = slides[slideIndex];
            const slideHeight = slide.offsetHeight;
            
            // Устанавливаем высоту контейнера равной высоте активного слайда
            slidesContainer.style.height = slideHeight + 'px';
        }
        
        // Функция для отображения слайда
        function showSlide(index) {
            if (isAnimating) return;
            isAnimating = true;
            
            // Запоминаем старый слайд для анимации
            const oldSlide = slides[currentSlide];
            
            // Удаляем класс active со старого слайда
            oldSlide.classList.remove('active');
            
            // Обновляем активную точку
            dots.forEach(dot => dot.classList.remove('active'));
            dots[index].classList.add('active');
            
            // Подготавливаем новый слайд к показу
            const newSlide = slides[index];
            
            // Вычисляем высоту нового слайда до того, как он станет видимым
            newSlide.style.visibility = 'hidden';
            newSlide.style.display = 'block';
            newSlide.style.position = 'absolute';
            newSlide.style.opacity = '0';
            
            // Принудительный reflow для получения корректного размера
            const newHeight = newSlide.offsetHeight;
            
            // Запускаем анимацию скрытия текущего слайда
            oldSlide.style.opacity = '0';
            
            setTimeout(() => {
                // Новый слайд уже позиционирован (position: absolute), начинаем анимацию высоты контейнера
                slidesContainer.style.height = newHeight + 'px';
                
                // Делаем новый слайд видимым, но оставляем его абсолютно позиционированным для анимации
                newSlide.style.visibility = 'visible';
                
                setTimeout(() => {
                    // Анимация появления нового слайда
                    newSlide.style.opacity = '1';
                    
                    // Добавляем класс appear к новому блоку для запуска анимации
                    const loreBlock = newSlide.querySelector('.lore-block');
                    if (loreBlock) {
                        loreBlock.classList.add('appear');
                    }
                    
                    // После завершения анимации устанавливаем финальное состояние
                    setTimeout(() => {
                        // Скрываем старый слайд
                        oldSlide.style.display = 'none';
                        oldSlide.style.position = '';
                        
                        // Делаем новый слайд относительно позиционированным (position: relative)
                        newSlide.style.position = 'relative';
                        
                        // Добавляем класс active к новому слайду
                        newSlide.classList.add('active');
                        
                        // Обновляем текущий индекс
                        currentSlide = index;
                        
                        // Снимаем блокировку анимации
                        isAnimating = false;
                    }, 500);
                }, 100);
            }, 300);
        }
        
        // Функция для перехода к следующему слайду
        function nextSlide() {
            const nextIndex = (currentSlide + 1) % slides.length;
            showSlide(nextIndex);
        }
        
        // Функция для перехода к предыдущему слайду
        function prevSlide() {
            const prevIndex = (currentSlide - 1 + slides.length) % slides.length;
            showSlide(prevIndex);
        }
        
        // Добавляем обработчики событий
        nextArrow.addEventListener('click', nextSlide);
        prevArrow.addEventListener('click', prevSlide);
        
        dots.forEach((dot, index) => {
            dot.addEventListener('click', () => {
                if (index !== currentSlide && !isAnimating) {
                    showSlide(index);
                }
            });
        });
        
        // Инициализируем первый слайд
        slides.forEach((slide, index) => {
            if (index === 0) {
                slide.style.display = 'block';
                slide.style.opacity = '1';
                slide.style.visibility = 'visible';
                slide.style.position = 'relative';
                
                // Добавляем класс active к первому слайду
                slide.classList.add('active');
                
                // Добавляем класс appear к первому блоку
                const loreBlock = slide.querySelector('.lore-block');
                if (loreBlock) {
                    loreBlock.classList.add('appear');
                }
            } else {
                slide.style.display = 'none';
                slide.style.opacity = '0';
                slide.style.visibility = 'hidden';
                slide.style.position = '';
                
                // Убираем класс active у неактивных слайдов
                slide.classList.remove('active');
            }
        });
        
        // Устанавливаем начальную высоту контейнера
        updateContainerHeight(0);
        
        // Обработчик изменения размера окна
        window.addEventListener('resize', () => {
            updateContainerHeight(currentSlide);
        });
    }
    
    // Функция для анимации лор-блоков при прокрутке
    function animateLoreBlocks() {
        const loreBlocks = document.querySelectorAll('.lore-block');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('appear');
                    // Отключаем наблюдение после появления
                    observer.unobserve(entry.target);
                }
            });
        }, {
            root: null, // наблюдаем относительно viewport
            threshold: 0.15, // когда 15% элемента видны
            rootMargin: '-50px' // небольшой отступ, чтобы элемент немного задержался перед анимацией
        });
        
        loreBlocks.forEach(block => {
            observer.observe(block);
        });
    }
    
    // Запускаем инициализацию слайдера
    initLoreSlider();
    
    // Запускаем анимацию лор-блоков
    animateLoreBlocks();
    
    // Плавный скролл для якорных ссылок
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                window.scrollTo({
                    top: target.offsetTop - 70, // Компенсация для шапки сайта
                    behavior: 'smooth'
                });
            }
        });
    });
    
});