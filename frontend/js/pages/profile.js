import { mountHeader } from '../components/header.js';
import { mountSidebar } from '../components/sidebar.js';
import { mountEmpty } from '../components/empty-state.js';
import { usersApi, categoriesApi } from '../api/users.js';
import { authApi } from '../api/auth.js';
import { enrollmentsApi } from '../api/enrollments.js';
import { toast } from '../components/toast.js';
import { escapeHtml, getQueryParam } from '../utils/dom.js';
import { formatDate, pluralize } from '../utils/format.js';

const LEVEL_ORDER = { beginner: 0, junior: 1, middle: 2, senior: 3 };

let me = null;
let categories = [];
let activeTab = 'personal';

document.addEventListener('DOMContentLoaded', async () => {
  me = await mountHeader('#header');
  if (!me) return;
  mountSidebar('#sidebar', me);
  categories = await categoriesApi.list();

  // Скрываем таб preferences для не-студентов
  if (me.role !== 'student') {
    document.querySelector('[data-tab="preferences"]')?.remove();
  }
  // Админу не нужен таб «Мои курсы» — он не записывается на обучение
  if (me.role === 'admin') {
    document.querySelector('[data-tab="courses"]')?.remove();
  }

  activeTab = getQueryParam('tab') || 'personal';
  // Если запрошен таб, который скрыт для текущей роли — откатываемся на personal
  if (!document.querySelector(`[data-tab="${activeTab}"]`)) {
    activeTab = 'personal';
  }
  setActiveTab(activeTab);

  // SPA-переключение: клик по табу не перезагружает страницу,
  // только перерисовывает tab-content и обновляет URL.
  document.querySelectorAll('#tabs .tab').forEach(t => {
    t.addEventListener('click', (e) => {
      e.preventDefault();
      const name = t.dataset.tab;
      if (!name || name === activeTab) return;
      activeTab = name;
      setActiveTab(name);
      history.replaceState({}, '', `?tab=${name}`);
      renderTab();
    });
  });

  renderTab();
});

function setActiveTab(name) {
  document.querySelectorAll('#tabs .tab').forEach(t => {
    t.classList.toggle('is-active', t.dataset.tab === name);
  });
}

function renderTab() {
  const root = document.getElementById('tab-content');
  // Единый лоадер до завершения отрисовки конкретного таба — устраняет
  // мигание «другой страницы» при переключении между вкладками.
  root.innerHTML = '<p class="muted" style="padding:24px 0">Загружаем…</p>';
  if (activeTab === 'personal') return renderPersonal(root);
  if (activeTab === 'preferences') return renderPreferences(root);
  if (activeTab === 'courses') return renderMyCourses(root);
  if (activeTab === 'security') return renderSecurity(root);
}

function renderPersonal(root) {
  root.innerHTML = `
    <div class="profile-block">
      <div class="form-row" style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div class="form-group">
          <label class="form-label">Имя</label>
          <input type="text" class="input" id="first_name" value="${escapeHtml(me.first_name)}">
        </div>
        <div class="form-group">
          <label class="form-label">Фамилия</label>
          <input type="text" class="input" id="last_name" value="${escapeHtml(me.last_name)}">
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Email</label>
        <input type="email" class="input" value="${escapeHtml(me.email)}" disabled>
      </div>
      <div class="form-group">
        <label class="form-label">Должность</label>
        <input type="text" class="input" id="position" value="${escapeHtml(me.position || '')}">
      </div>
      <div class="form-group">
        <label class="form-label">Телефон</label>
        <input type="text" class="input" id="phone" value="${escapeHtml(me.phone || '')}">
      </div>
      <div class="form-group">
        <label class="form-label">О себе</label>
        <textarea class="textarea" id="bio">${escapeHtml(me.bio || '')}</textarea>
      </div>
      <button class="btn btn-primary" id="save-personal">Сохранить</button>
    </div>
  `;
  document.getElementById('save-personal').addEventListener('click', async () => {
    try {
      me = await usersApi.updateMe({
        first_name: document.getElementById('first_name').value.trim(),
        last_name: document.getElementById('last_name').value.trim(),
        position: document.getElementById('position').value.trim() || null,
        phone: document.getElementById('phone').value.trim() || null,
        bio: document.getElementById('bio').value,
      });
      toast.success('Сохранено');
    } catch (err) {
      toast.error(err.message || 'Ошибка');
    }
  });
}

function renderPreferences(root) {
  const dirs = new Set(me.directions || []);
  root.innerHTML = `
    <div class="profile-block">
      <div class="plate plate--warning mb-16">
        <i data-lucide="alert-triangle"></i>
        <span>Курсы, на которые вы записаны и не входят в новую программу, останутся в «Мои курсы», но в каталоге не будут показываться.</span>
      </div>
      <h3 class="mb-8">Направления</h3>
      <div class="preferences__directions" id="prefs-dirs">
        ${categories.map(c => `
          <button type="button" class="check-card ${dirs.has(c.id) ? 'is-active' : ''}" data-id="${c.id}">
            <span class="check-card__icon"><i data-lucide="${escapeHtml(c.icon_name || 'circle')}" style="width:20px;height:20px"></i></span>
            <span class="check-card__title">${escapeHtml(c.name)}</span>
          </button>
        `).join('')}
      </div>
      <h3 class="mb-8">Текущий уровень</h3>
      <div class="level-group" id="prefs-current">
        ${['beginner', 'junior', 'middle'].map(l => `
          <button type="button" class="level-btn ${me.current_level === l ? 'is-active' : ''}" data-value="${l}">${l}</button>
        `).join('')}
      </div>
      <h3 class="mb-8 mt-16">Желаемый уровень</h3>
      <div class="level-group" id="prefs-target">
        ${['junior', 'middle', 'senior'].map(l => `
          <button type="button" class="level-btn ${me.target_level === l ? 'is-active' : ''}" data-value="${l}">${l}</button>
        `).join('')}
      </div>
      <button class="btn btn-primary mt-24" id="save-prefs">Сохранить программу</button>
    </div>
  `;
  if (window.lucide) window.lucide.createIcons();

  const state = {
    directions: new Set(me.directions || []),
    current_level: me.current_level,
    target_level: me.target_level,
  };

  root.querySelector('#prefs-dirs').addEventListener('click', (e) => {
    const card = e.target.closest('.check-card');
    if (!card) return;
    const id = parseInt(card.dataset.id, 10);
    if (state.directions.has(id)) { state.directions.delete(id); card.classList.remove('is-active'); }
    else { state.directions.add(id); card.classList.add('is-active'); }
  });
  function setupLevel(rootId, key) {
    const lr = document.getElementById(rootId);
    lr.addEventListener('click', (e) => {
      const btn = e.target.closest('.level-btn');
      if (!btn || btn.disabled) return;
      lr.querySelectorAll('.level-btn').forEach(b => b.classList.remove('is-active'));
      btn.classList.add('is-active');
      state[key] = btn.dataset.value;
      if (key === 'current_level') {
        const tgt = document.getElementById('prefs-target');
        tgt.querySelectorAll('.level-btn').forEach(b => {
          const lower = LEVEL_ORDER[b.dataset.value] < LEVEL_ORDER[state.current_level];
          b.disabled = lower;
          if (lower && b.classList.contains('is-active')) {
            b.classList.remove('is-active');
            state.target_level = null;
          }
        });
      }
    });
  }
  setupLevel('prefs-current', 'current_level');
  setupLevel('prefs-target', 'target_level');

  document.getElementById('save-prefs').addEventListener('click', async () => {
    if (state.directions.size === 0) {
      toast.error('Выберите хотя бы одно направление');
      return;
    }
    try {
      me = await usersApi.updateMe({
        directions: Array.from(state.directions),
        current_level: state.current_level,
        target_level: state.target_level,
      });
      toast.success('Программа обновлена. Каталог пересобран');
    } catch (err) {
      toast.error(err.message || 'Ошибка');
    }
  });
}

async function renderMyCourses(root) {
  root.innerHTML = '<p class="muted">Загружаем…</p>';
  try {
    const res = await enrollmentsApi.list();
    if (!res.items.length) {
      mountEmpty(root, {
        title: 'Вы ещё не записались на курс',
        description: 'Откройте каталог',
        actionText: 'Открыть каталог',
        actionHref: '/pages/catalog.html',
      });
      return;
    }
    root.innerHTML = `
      <div class="tabs" id="status-tabs" style="margin-bottom:16px">
        <a class="tab is-active" data-status="all" href="javascript:void(0)">Все</a>
        <a class="tab" data-status="active" href="javascript:void(0)">В процессе</a>
        <a class="tab" data-status="completed" href="javascript:void(0)">Завершённые</a>
      </div>
      <div class="my-courses-grid" id="my-courses-grid"></div>
    `;
    function renderGrid(filter) {
      const filtered = filter === 'all' ? res.items : res.items.filter(e => e.status === filter);
      const grid = document.getElementById('my-courses-grid');
      grid.innerHTML = filtered.map(e => `
        <a class="my-course-card card--clickable" href="/pages/course.html?id=${e.course_id}">
          <div class="my-course-card__plate">
            <i data-lucide="book-open"></i>
            ${escapeHtml(e.course_title || '')}
          </div>
          <div class="my-course-card__body">
            <div class="my-course-card__meta">
              ${e.progress_percent}% · ${e.lessons_completed} из ${e.lessons_total}
              ${pluralize(e.lessons_total, ['урока', 'уроков', 'уроков'])}
            </div>
            <div class="progress"><div class="progress__fill" style="width:${e.progress_percent}%"></div></div>
            <div class="my-course-card__status">
              ${e.status === 'completed'
                ? `<span class="badge badge--success">Завершён · ${formatDate(e.completed_at)}</span>`
                : `<span class="badge badge--primary">В процессе</span>`}
            </div>
          </div>
        </a>
      `).join('') || '<p class="muted">Нет курсов в этом статусе</p>';
      if (window.lucide) window.lucide.createIcons();
    }
    renderGrid('all');
    document.querySelectorAll('#status-tabs .tab').forEach(t => {
      t.addEventListener('click', () => {
        document.querySelectorAll('#status-tabs .tab').forEach(x => x.classList.remove('is-active'));
        t.classList.add('is-active');
        renderGrid(t.dataset.status);
      });
    });
  } catch (err) {
    root.innerHTML = `<p class="muted">${escapeHtml(err.message || '')}</p>`;
  }
}

function renderSecurity(root) {
  root.innerHTML = `
    <div class="profile-block">
      <h3 class="mb-16">Смена пароля</h3>
      <div class="form-group">
        <label class="form-label">Текущий пароль</label>
        <input type="password" class="input" id="cur-pwd">
      </div>
      <div class="form-group">
        <label class="form-label">Новый пароль (минимум 8 символов)</label>
        <input type="password" class="input" id="new-pwd">
      </div>
      <button class="btn btn-primary" id="save-pwd">Сменить пароль</button>
    </div>
  `;
  document.getElementById('save-pwd').addEventListener('click', async () => {
    const cur = document.getElementById('cur-pwd').value;
    const next = document.getElementById('new-pwd').value;
    if (next.length < 8) { toast.error('Минимум 8 символов'); return; }
    try {
      await authApi.changePassword(cur, next);
      toast.success('Пароль изменён. Войдите заново');
      setTimeout(() => location.replace('/pages/login.html'), 1500);
    } catch (err) {
      toast.error(err.message || 'Ошибка');
    }
  });
}
