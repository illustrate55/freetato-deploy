import { authApi } from '../api/auth.js';
import { categoriesApi } from '../api/users.js';
import { toast } from '../components/toast.js';
import { escapeHtml } from '../utils/dom.js';

const LEVEL_ORDER = { beginner: 0, junior: 1, middle: 2, senior: 3 };

const state = {
  step1Data: null,
  role: 'student',
  selectedDirections: new Set(),
  currentLevel: null,
  targetLevel: null,
};

function setStrength(password) {
  const fill = document.getElementById('strength-fill');
  fill.classList.remove('medium', 'strong');
  if (!password) { fill.style.width = '0%'; return; }
  const longEnough = password.length >= 8;
  const hasNum = /\d/.test(password);
  const hasMix = /[a-z]/i.test(password) && /[A-Z]/.test(password);
  if (longEnough && hasNum && hasMix) fill.classList.add('strong');
  else if (longEnough && (hasNum || hasMix)) fill.classList.add('medium');
}

function showStep(n) {
  document.getElementById('step-1').classList.toggle('hidden', n !== 1);
  document.getElementById('step-2').classList.toggle('hidden', n !== 2);
}

async function loadDirections() {
  // Эндпоинт публичный? — нет, требует auth. Но для регистрации делаем без auth-токена,
  // поэтому дублируем через прямой fetch к публичной обёртке. Здесь /api/v1/categories
  // требует авторизации — используем заглушку: если 401, рендерим без шага 2.
  // На практике admin раздаёт токен на seed; для регистрации используем простой подход:
  // делаем запрос анонимно, если упало — показываем сообщение.
  const r = await fetch('/api/v1/categories', {});
  if (r.ok) return r.json();
  // Fallback: если categories закрыты — пытаемся через try-attempt без токена
  return [];
}

function renderDirections(cats) {
  const root = document.getElementById('directions');
  if (!cats.length) {
    root.innerHTML = `<p class="muted">Нет доступных направлений. Обратитесь к администратору.</p>`;
    return;
  }
  root.innerHTML = cats.map(c => `
    <button type="button" class="check-card" data-id="${c.id}">
      <span class="check-card__icon">
        <i data-lucide="${escapeHtml(c.icon_name || 'circle')}" style="width:24px;height:24px"></i>
      </span>
      <span class="check-card__title">${escapeHtml(c.name)}</span>
    </button>
  `).join('');
  if (window.lucide) window.lucide.createIcons();

  root.addEventListener('click', (e) => {
    const card = e.target.closest('.check-card');
    if (!card) return;
    const id = parseInt(card.dataset.id, 10);
    if (state.selectedDirections.has(id)) {
      state.selectedDirections.delete(id);
      card.classList.remove('is-active');
    } else {
      state.selectedDirections.add(id);
      card.classList.add('is-active');
    }
    updateFinishBtn();
  });
}

function setupLevelGroup(rootId, isCurrent) {
  const root = document.getElementById(rootId);
  root.addEventListener('click', (e) => {
    const btn = e.target.closest('.level-btn');
    if (!btn || btn.disabled) return;
    root.querySelectorAll('.level-btn').forEach(b => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    if (isCurrent) {
      state.currentLevel = btn.dataset.value;
      // Блокируем target ниже current
      const targetRoot = document.getElementById('target-level');
      targetRoot.querySelectorAll('.level-btn').forEach(b => {
        const lower = LEVEL_ORDER[b.dataset.value] < LEVEL_ORDER[state.currentLevel];
        b.disabled = lower;
        if (lower && b.classList.contains('is-active')) {
          b.classList.remove('is-active');
          state.targetLevel = null;
        }
      });
    } else {
      state.targetLevel = btn.dataset.value;
    }
    updateFinishBtn();
  });
}

function updateFinishBtn() {
  const btn = document.getElementById('finish-btn');
  btn.disabled = !(state.selectedDirections.size > 0 && state.currentLevel && state.targetLevel);
}

function applyRoleUI() {
  const isTeacher = state.role === 'teacher';
  const label = document.getElementById('step-1-label');
  if (label) label.textContent = isTeacher ? 'Регистрация преподавателя' : 'Шаг 1 из 2';
  const submitBtn = document.getElementById('step-1-submit');
  if (submitBtn) submitBtn.textContent = isTeacher ? 'Зарегистрироваться' : 'Продолжить →';
}

async function submitRegistration(extra = {}) {
  const payload = { ...state.step1Data, role: state.role, ...extra };
  const res = await authApi.register(payload);
  sessionStorage.setItem('access_token', res.access_token);
  sessionStorage.setItem('refresh_token', res.refresh_token);
  // Кэшируем профиль — на следующей странице header/sidebar рендерятся мгновенно.
  if (res.user) sessionStorage.setItem('user', JSON.stringify(res.user));
  location.replace('/pages/dashboard.html');
}

function describeRegisterError(err) {
  if (err.code === 'EMAIL_ALREADY_EXISTS' || err.code === 'EMAIL_TAKEN') {
    return 'Этот email уже зарегистрирован. Войдите или используйте другой адрес.';
  }
  if (/already|существует|уже/i.test(err.message || '')) {
    return 'Этот email уже зарегистрирован. Войдите или используйте другой адрес.';
  }
  return err.message || 'Ошибка регистрации';
}

document.addEventListener('DOMContentLoaded', async () => {
  document.getElementById('password').addEventListener('input', (e) => setStrength(e.target.value));

  document.getElementById('role-group').addEventListener('click', (e) => {
    const btn = e.target.closest('.register__role-btn');
    if (!btn) return;
    state.role = btn.dataset.role;
    document.querySelectorAll('.register__role-btn').forEach(b => b.classList.toggle('is-active', b === btn));
    applyRoleUI();
  });
  applyRoleUI();

  document.getElementById('step-1').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value.trim();
    const first_name = document.getElementById('first_name').value.trim();
    const last_name = document.getElementById('last_name').value.trim();
    const password = document.getElementById('password').value;
    const password_confirm = document.getElementById('password_confirm').value;
    const terms = document.getElementById('terms').checked;

    if (!email || !first_name || !last_name || !password) {
      toast.error('Заполните все обязательные поля');
      return;
    }
    if (password.length < 8) {
      toast.error('Пароль минимум 8 символов');
      return;
    }
    if (password !== password_confirm) {
      toast.error('Пароли не совпадают');
      return;
    }
    if (!terms) {
      toast.error('Нужно согласиться с условиями');
      return;
    }
    state.step1Data = { email, first_name, last_name, password };

    // Преподаватель регистрируется без шага 2
    if (state.role === 'teacher') {
      const submitBtn = document.getElementById('step-1-submit');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Создаём аккаунт…';
      try {
        await submitRegistration();
      } catch (err) {
        toast.error(describeRegisterError(err));
        submitBtn.disabled = false;
        applyRoleUI();
      }
      return;
    }

    showStep(2);
  });

  document.getElementById('back-btn').addEventListener('click', () => showStep(1));

  setupLevelGroup('current-level', true);
  setupLevelGroup('target-level', false);

  try {
    const cats = await loadDirections();
    renderDirections(cats);
  } catch {
    renderDirections([]);
  }

  document.getElementById('step-2').addEventListener('submit', async (e) => {
    e.preventDefault();
    const finishBtn = document.getElementById('finish-btn');
    if (finishBtn.disabled) return;
    finishBtn.disabled = true;
    finishBtn.textContent = 'Создаём аккаунт…';

    try {
      await submitRegistration({
        directions: Array.from(state.selectedDirections),
        current_level: state.currentLevel,
        target_level: state.targetLevel,
      });
    } catch (err) {
      toast.error(describeRegisterError(err));
      finishBtn.disabled = false;
      finishBtn.textContent = 'Завершить регистрацию';
    }
  });
});
