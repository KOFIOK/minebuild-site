/**
 * Главный JavaScript файл для главной страницы MineBuild
 */

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация обработчиков копирования IP
    initCopyIpButtons();
    
    // Инициализация системы частиц, если библиотека доступна
    initParticles();
    
    // Инициализация прокрутки страницы
    initScrollIndicator();
    
    // Анимация для выделенных слов
    initHighlightWords();
    
    // Инициализация параллакс-эффектов
    initParallaxEffect();
    
    // Анимация шагов "Как начать игру"
    initStepsAnimation();
});

/**
 * Инициализация кнопок копирования IP-адреса
 */
function initCopyIpButtons() {
    document.querySelectorAll('.copy-ip').forEach(button => {
        button.addEventListener('click', function() {
            const ip = this.dataset.ip;
            navigator.clipboard.writeText(ip).then(() => {
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-check me-2"></i>IP СКОПИРОВАН <span class="shimmer"></span>';
                setTimeout(() => {
                    this.innerHTML = originalText;
                }, 2000);
            });
        });
    });
}

/**
 * Инициализация системы частиц
 */
function initParticles() {
    if (typeof particlesJS !== 'undefined') {
        particlesJS('particles-js', {
            "particles": {
                "number": {
                    "value": 30,
                    "density": {
                        "enable": true,
                        "value_area": 800
                    }
                },
                "color": {
                    "value": "#00E5A1"
                },
                "shape": {
                    "type": "circle",
                    "stroke": {
                        "width": 0,
                        "color": "#000000"
                    },
                    "polygon": {
                        "nb_sides": 5
                    }
                },
                "opacity": {
                    "value": 0.3,
                    "random": true,
                    "anim": {
                        "enable": true,
                        "speed": 0.5,
                        "opacity_min": 0.1,
                        "sync": false
                    }
                },
                "size": {
                    "value": 5,
                    "random": true,
                    "anim": {
                        "enable": true,
                        "speed": 2,
                        "size_min": 0.1,
                        "sync": false
                    }
                },
                "line_linked": {
                    "enable": true,
                    "distance": 150,
                    "color": "#00E5A1",
                    "opacity": 0.2,
                    "width": 1
                },
                "move": {
                    "enable": true,
                    "speed": 1,
                    "direction": "none",
                    "random": true,
                    "straight": false,
                    "out_mode": "out",
                    "bounce": false,
                    "attract": {
                        "enable": true,
                        "rotateX": 600,
                        "rotateY": 1200
                    }
                }
            },
            "interactivity": {
                "detect_on": "canvas",
                "events": {
                    "onhover": {
                        "enable": true,
                        "mode": "grab"
                    },
                    "onclick": {
                        "enable": true,
                        "mode": "push"
                    },
                    "resize": true
                },
                "modes": {
                    "grab": {
                        "distance": 140,
                        "line_linked": {
                            "opacity": 0.5
                        }
                    },
                    "push": {
                        "particles_nb": 3
                    }
                }
            },
            "retina_detect": true
        });
    }
}

/**
 * Инициализация индикатора прокрутки
 */
function initScrollIndicator() {
    const scrollIndicator = document.querySelector('.scroll-indicator');
    if (scrollIndicator) {
        scrollIndicator.addEventListener('click', function() {
            document.querySelector('.how-to-start-section').scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        });
    }
}

/**
 * Анимация для выделенных слов
 */
function initHighlightWords() {
    const highlightWords = document.querySelectorAll('.highlight-word');
    
    // Используем IntersectionObserver для активации анимации при прокрутке
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('highlight-active');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    highlightWords.forEach(word => {
        observer.observe(word);
    });
}

/**
 * Инициализация параллакс-эффекта для плавающих блоков
 */
function initParallaxEffect() {
    const blocks = document.querySelectorAll('.floating-block');
    if (blocks.length === 0) return;
    
    // Переменные для отслеживания позиции мыши с плавным переходом
    let mouseX = 0;
    let mouseY = 0;
    let targetMouseX = 0;
    let targetMouseY = 0;
    
    // Обработчик движения мыши для параллакс-эффекта
    window.addEventListener('mousemove', function(e) {
        // Нормализованные координаты курсора (от 0 до 1)
        targetMouseX = e.clientX / window.innerWidth;
        targetMouseY = e.clientY / window.innerHeight;
    });
    
    // Плавное обновление позиции блоков
    function updateParallax() {
        // Плавно обновляем текущую позицию мыши
        mouseX += (targetMouseX - mouseX) * 0.05;
        mouseY += (targetMouseY - mouseY) * 0.05;
        
        blocks.forEach((block, index) => {
            // Разные блоки перемещаются с разной скоростью для эффекта глубины
            const factor = (index + 1) * 10;
            const offsetX = (mouseX - 0.5) * factor;
            const offsetY = (mouseY - 0.5) * factor;
            
            // Применяем трансформацию с плавным переходом
            block.style.transform = `translate3d(${offsetX}px, ${offsetY}px, 0)`;
        });
        
        requestAnimationFrame(updateParallax);
    }
    
    // Запускаем анимацию
    updateParallax();
}

/**
 * Анимация шагов "Как начать игру"
 */
function initStepsAnimation() {
    const stepItems = document.querySelectorAll('.step-item');
    if (stepItems.length === 0) return;
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animated');
                // Добавляем небольшую задержку в зависимости от номера шага
                const stepNumber = entry.target.dataset.step;
                entry.target.style.transitionDelay = `${(stepNumber - 1) * 0.2}s`;
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.3 });

    stepItems.forEach(item => {
        observer.observe(item);
    });
}