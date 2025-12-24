// Модальное окно 
function openModal() { document.getElementById('authorModal').style.display = 'block'; }
function closeModal(event) {
    if (event.target.id === 'authorModal') {
        document.getElementById('authorModal').style.display = 'none';
    }
}

// Управление состоянием (History) 
let history = [];
let historyIndex = -1;
const MAX_HISTORY = 15;

const inputIds = [
    'brightness', 'contrast', 'saturation', 'sharpness',
    'color_r', 'color_g', 'color_b',
    'vignette', 'blur',
    'grayscale', 'sepia', 'negative'
];

const defaultState = {
    rotation: 0, flip_x: false, flip_y: false,
    brightness: 1.0, contrast: 1.0, saturation: 1.0, sharpness: 1.0,
    color_r: 1.0, color_g: 1.0, color_b: 1.0,
    vignette: 0, blur: 0,
    grayscale: false, sepia: false, negative: false
};

function getCurrentState() {
    let s = {};
    inputIds.forEach(k => {
        const el = document.getElementById(k);
        if(el) s[k] = el.type === 'checkbox' ? el.checked : parseFloat(el.value);
    });
    // Геометрия не хранится в input, берем из текущей истории или дефолт
    if (historyIndex >= 0) {
        s.rotation = history[historyIndex].rotation;
        s.flip_x = history[historyIndex].flip_x;
        s.flip_y = history[historyIndex].flip_y;
    } else {
        s.rotation = 0; s.flip_x = false; s.flip_y = false;
    }
    return s;
}

function applyStateToUI(state) {
    inputIds.forEach(k => {
        const el = document.getElementById(k);
        if (!el) return;
        if (el.type === 'checkbox') el.checked = state[k];
        else {
            el.value = state[k];
            const valDisplay = document.getElementById('val-' + k);
            if(valDisplay) valDisplay.innerText = state[k];
        }
    });
}

// Логика Геометрии 
function rotate(deg) {
    let s = getCurrentState();
    s.rotation = (s.rotation + deg) % 360;
    pushHistory(s);
    sendUpdate(s);
}

function flip(axis) {
    let s = getCurrentState();
    if(axis === 'x') s.flip_x = !s.flip_x;
    if(axis === 'y') s.flip_y = !s.flip_y;
    pushHistory(s);
    sendUpdate(s);
}

// Логика Истории 
function pushHistory(state) {
    if (historyIndex < history.length - 1) history = history.slice(0, historyIndex + 1);
    history.push({...state});
    if (history.length > MAX_HISTORY) history.shift(); else historyIndex++;
    updateHistoryButtons();
}

function updateHistoryButtons() {
    document.getElementById('btnUndo').disabled = (historyIndex <= 0);
    document.getElementById('btnRedo').disabled = (historyIndex >= history.length - 1);
}

function historyUndo() {
    if (historyIndex > 0) {
        historyIndex--;
        const state = history[historyIndex];
        applyStateToUI(state);
        sendUpdate(state);
        updateHistoryButtons();
    }
}

function historyRedo() {
    if (historyIndex < history.length - 1) {
        historyIndex++;
        const state = history[historyIndex];
        applyStateToUI(state);
        sendUpdate(state);
        updateHistoryButtons();
    }
}

// Взаимодействие с UI
function initHistory() {
    history = []; historyIndex = -1;
    let s = {...defaultState};
    applyStateToUI(s);
    pushHistory(s);
}

function liveUpdate(id) {
    const val = document.getElementById(id).value;
    const disp = document.getElementById('val-' + id);
    if(disp) disp.innerText = val;
    debouncedSend();
}

function commitState(force = false) {
    const s = getCurrentState();
    pushHistory(s);
    if(force) sendUpdate(s); else debouncedSend();
}

// Debounce для плавности
function debounce(func, timeout = 100){
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => { func.apply(this, args); }, timeout);
    };
}

const loader = document.getElementById('loader');
const previewImg = document.getElementById('previewImage');
const downloadBtn = document.getElementById('downloadBtn');
const placeholder = document.getElementById('placeholder');

// Отправка данных на сервер 
async function sendUpdate(stateOverride = null) {
    if (!previewImg.src || previewImg.classList.contains('hidden')) return;
    const state = stateOverride || getCurrentState();
    
    loader.style.display = 'block';
    
    try {
        const res = await fetch('/process', {
            method: 'POST', 
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(state)
        });
        const data = await res.json();
        if (data.status === 'success') {
            previewImg.src = 'data:image/jpeg;base64,' + data.image;
        }
    } catch (err) { 
        console.error(err); 
    } finally { 
        loader.style.display = 'none'; 
    }
}

const debouncedSend = debounce(() => sendUpdate(), 200);

// Загрузка файла
document.getElementById('fileInput').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const fd = new FormData(); 
    fd.append('image', file);
    
    placeholder.style.display = 'none';
    loader.style.display = 'block';
    
    try {
        const res = await fetch('/upload', { method: 'POST', body: fd });
        const data = await res.json();
        
        if (data.status === 'success') {
            previewImg.src = 'data:image/jpeg;base64,' + data.image;
            previewImg.classList.remove('hidden');
            downloadBtn.disabled = false;
            initHistory();
        } else {
            alert(data.message || 'Ошибка загрузки');
        }
    } catch (err) { 
        alert('Ошибка соединения с сервером'); 
    } finally { 
        loader.style.display = 'none'; 
    }
});

function resetAll() {
    initHistory();
    sendUpdate(defaultState);
}

// Скачивание
async function downloadImage() {
    if(downloadBtn.disabled) return;
    const link = document.createElement('a');
    // Проверка расширения
    const isPng = previewImg.src.includes('image/png');
    link.href = previewImg.src;
    link.download = isPng ? 'pyweb_edit.png' : 'pyweb_edit.jpg';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}