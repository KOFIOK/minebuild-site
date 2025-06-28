// Управление скрывающимся навбаром
document.addEventListener('DOMContentLoaded', function() {
    const navbar = document.querySelector('.navbar');
    let lastScrollY = window.scrollY;
    let mousedOverTopArea = false;
    let ticking = false;
    let isScrollingUp = false;
    let dropdownOpen = false; // Добавляем отслеживание состояния dropdown
    const navbarHeight = navbar ? navbar.offsetHeight : 80;
    const topAreaSensitivity = 50; // Верхние 50px экрана

    // Добавляем класс для начального состояния
    if (navbar) {
        navbar.classList.add('nav-visible');
    }

    // Отслеживание состояния dropdown меню
    function setupDropdownTracking() {
        const dropdownElements = navbar.querySelectorAll('.dropdown');
        
        dropdownElements.forEach(dropdown => {
            // Отслеживаем открытие dropdown
            dropdown.addEventListener('show.bs.dropdown', function() {
                dropdownOpen = true;
                // Принудительно показываем навбар когда открывается dropdown
                navbar.classList.remove('nav-hidden');
                navbar.classList.add('nav-visible');
            });
            
            // Отслеживаем закрытие dropdown
            dropdown.addEventListener('hide.bs.dropdown', function() {
                dropdownOpen = false;
            });
        });
    }

    // Функция для обработки скролла
    function handleScroll() {
        const currentScrollY = window.scrollY;
        
        // Определяем направление скролла
        isScrollingUp = currentScrollY < lastScrollY;

        // Логика показа/скрытия навбара (не скрываем если dropdown открыт)
        if (!mousedOverTopArea && !dropdownOpen) {
            if (currentScrollY > navbarHeight) {
                // Скроллинг вниз и не наверху - скрываем навбар
                if (currentScrollY > lastScrollY + 5) { // Добавлен порог для предотвращения нежелательной реакции
                    navbar.classList.remove('nav-visible');
                    navbar.classList.add('nav-hidden');
                }
                // Скроллинг вверх - показываем навбар
                else if (isScrollingUp && currentScrollY < lastScrollY - 5) { // Порог для более стабильного поведения
                    navbar.classList.remove('nav-hidden');
                    navbar.classList.add('nav-visible');
                }
            } else {
                // В начале страницы - всегда показываем навбар
                navbar.classList.remove('nav-hidden');
                navbar.classList.add('nav-visible');
            }
        }

        lastScrollY = currentScrollY;
        ticking = false;
    }

    // Оптимизация вызовов обработчика скролла с дебаунсингом
    let scrollTimeout;
    window.addEventListener('scroll', function() {
        if (!ticking) {
            // Отменяем предыдущий запланированный вызов, если он ещё не выполнен
            if (scrollTimeout) {
                cancelAnimationFrame(scrollTimeout);
            }
            
            // Планируем новый вызов
            scrollTimeout = requestAnimationFrame(handleScroll);
            ticking = true;
        }
    });

    // Обработка наведения курсора на верхнюю часть экрана
    document.addEventListener('mousemove', function(e) {
        const wasInTopArea = mousedOverTopArea;
        
        // Если курсор находится в верхней части экрана (топ-зоне)
        mousedOverTopArea = e.clientY <= topAreaSensitivity;
        
        // Показываем навбар только когда курсор входит в верхнюю область
        if (mousedOverTopArea && !wasInTopArea) {
            navbar.classList.remove('nav-hidden');
            navbar.classList.add('nav-visible');
        }
        // Если мышь покидает верхнюю область и мы прокручиваем вниз
        else if (!mousedOverTopArea && wasInTopArea && !isScrollingUp && window.scrollY > navbarHeight) {
            navbar.classList.remove('nav-visible');
            navbar.classList.add('nav-hidden');
        }
    });
    
    // Добавим событие для самого навбара - при наведении всегда виден
    navbar.addEventListener('mouseenter', function() {
        navbar.classList.remove('nav-hidden');
        navbar.classList.add('nav-visible');
    });

    // Инициализируем отслеживание dropdown меню
    setupDropdownTracking();
});