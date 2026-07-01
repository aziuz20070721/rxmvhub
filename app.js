let allVideos = [];
let allCategories = [];
let currentCategory = 'all';
let searchQuery = '';
let debounceTimeout = null;

// Загрузка данных из data.json на GitHub
async function loadData() {
    const loader = document.querySelector('.loader');
    const grid = document.querySelector('.video-grid');
    const noResults = document.querySelector('.no-results');
    
    loader.style.display = 'flex';
    grid.innerHTML = '';
    noResults.style.display = 'none';

    try {
        // Загружаем прямо с GitHub Raw
        const url = `https://raw.githubusercontent.com/aziuz20070721/rxmvhub/main/data.json?t=${Date.now()}`;
        const resp = await fetch(url, {
            headers: {
                'Accept': 'application/json'
            }
        });
        
        if (!resp.ok) throw new Error(`HTTP error! status: ${resp.status}`);
        
        const data = await resp.json();
        allVideos = data.videos || [];
        allCategories = data.categories || [];
        
        if (allVideos.length === 0) {
            grid.innerHTML = '<div style="text-align:center; padding:40px; color: var(--text-secondary);">📦 Видео еще не загружены. Парсер работает...</div>';
            return;
        }
        
        renderCategories();
        renderVideos();
    } catch (err) {
        console.error('Ошибка загрузки:', err);
        grid.innerHTML = `<div style="text-align:center; padding:40px; color: var(--text-secondary);">❌ Ошибка загрузки видео<br><small>${err.message}</small></div>`;
    } finally {
        loader.style.display = 'none';
    }
}

// Рендер кнопок категорий
function renderCategories() {
    const container = document.querySelector('.categories');
    if (!container) return;
    container.innerHTML = '';
    
    // Кнопка "Все"
    const allBtn = document.createElement('button');
    allBtn.className = 'category-btn' + (currentCategory === 'all' ? ' active' : '');
    allBtn.textContent = 'Все';
    allBtn.addEventListener('click', () => {
        currentCategory = 'all';
        updateActiveCategory(allBtn);
        renderVideos();
    });
    container.appendChild(allBtn);
    
    // Категории из data.json
    allCategories.forEach(cat => {
        const btn = document.createElement('button');
        btn.className = 'category-btn' + (currentCategory === cat ? ' active' : '');
        btn.textContent = cat;
        btn.addEventListener('click', () => {
            currentCategory = cat;
            updateActiveCategory(btn);
            renderVideos();
        });
        container.appendChild(btn);
    });
}

function updateActiveCategory(activeBtn) {
    document.querySelectorAll('.category-btn').forEach(btn => btn.classList.remove('active'));
    activeBtn.classList.add('active');
}

// Фильтрация видео
function filterVideos() {
    let filtered = allVideos;
    if (currentCategory !== 'all') {
        filtered = filtered.filter(v => v.category === currentCategory);
    }
    if (searchQuery.trim() !== '') {
        const q = searchQuery.toLowerCase();
        filtered = filtered.filter(v => v.title.toLowerCase().includes(q));
    }
    return filtered;
}

// Рендер карточек
function renderVideos() {
    const filtered = filterVideos();
    const grid = document.querySelector('.video-grid');
    const noResults = document.querySelector('.no-results');
    
    if (!grid) return;
    grid.innerHTML = '';
    
    if (filtered.length === 0) {
        noResults.style.display = 'block';
        return;
    }
    noResults.style.display = 'none';
    
    filtered.forEach(video => {
        const card = createVideoCard(video);
        grid.appendChild(card);
    });
}

// Создание карточки
function createVideoCard(video) {
    const card = document.createElement('div');
    card.className = 'video-card';
    
    const thumbDiv = document.createElement('div');
    thumbDiv.className = 'video-thumbnail';
    const img = document.createElement('img');
    img.src = video.thumbnail;
    img.alt = video.title;
    img.onerror = () => {
        img.src = 'https://via.placeholder.com/320x180?text=No+preview';
    };
    thumbDiv.appendChild(img);
    
    const infoDiv = document.createElement('div');
    infoDiv.className = 'video-info';
    const titleP = document.createElement('p');
    titleP.className = 'video-title';
    titleP.textContent = video.title;
    const catSpan = document.createElement('span');
    catSpan.className = 'video-category';
    catSpan.textContent = video.category;
    infoDiv.appendChild(titleP);
    infoDiv.appendChild(catSpan);
    
    card.appendChild(thumbDiv);
    card.appendChild(infoDiv);
    
    card.addEventListener('click', () => {
        window.open(video.url, '_blank');
    });
    
    return card;
}

// Поиск с debounce
function initSearch() {
    const searchInput = document.querySelector('.search-bar');
    if (!searchInput) return;
    searchInput.addEventListener('input', (e) => {
        if (debounceTimeout) clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {
            searchQuery = e.target.value;
            renderVideos();
        }, 300);
    });
}

// Инициализация Telegram WebApp
function initTelegram() {
    if (window.Telegram && Telegram.WebApp) {
        Telegram.WebApp.ready();
        Telegram.WebApp.expand();
        Telegram.WebApp.setHeaderColor('#000000');
    }
}

// Запуск
document.addEventListener('DOMContentLoaded', () => {
    initTelegram();
    loadData();
    initSearch();
});
