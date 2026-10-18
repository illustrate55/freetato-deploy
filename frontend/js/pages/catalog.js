import { mountHeader } from '../components/header.js';
import { mountSidebar } from '../components/sidebar.js';
import { mountEmpty } from '../components/empty-state.js';
import { coursesApi } from '../api/courses.js';
import { categoriesApi } from '../api/users.js';
import { escapeHtml } from '../utils/dom.js';
import { formatLevel, pluralize } from '../utils/format.js';

let categories = [];
let me = null;
let searchTimer = null;

document.addEventListener('DOMContentLoaded', async () => {
  me = await mountHeader('#header');
  if (!me) return;
  if (me.role === 'admin') { location.replace('/pages/admin.html'); return; }
  mountSidebar('#sidebar', me);

  // Для teacher/admin показываем фильтр статуса
  if (me.role !== 'student') {
    document.getElementById('status-filter-wrap').classList.remove('hidden');
  }

  categories = await categoriesApi.list();
  const sel = document.getElementById('category');
  categories.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = c.name;
    sel.appendChild(opt);
  });

  if (me.role === 'student') renderProfilePlate();

  ['search', 'level', 'category', 'status'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', debounceLoad);
    if (el && el.tagName === 'SELECT') el.addEventListener('change', loadCourses);
  });

  await loadCourses();
});

function debounceLoad() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadCourses, 400);
}

function renderProfilePlate() {
  const root = document.getElementById('profile-plate');
  const dirNames = (me.directions || [])
    .map(id => categories.find(c => c.id === id)?.name)
    .filter(Boolean)
    .join(', ');
  if (!dirNames) {
    root.classList.remove('hidden');
    root.className = 'plate plate--warning mb-16';
    root.innerHTML = `
      <i data-lucide="alert-triangle"></i>
      <span>Профиль обучения не настроен. <a href="/pages/profile.html?tab=preferences" class="link">Настроить</a></span>
    `;
    if (window.lucide) window.lucide.createIcons();
    return;
  }
  root.classList.remove('hidden');
  root.className = 'plate mb-16';
  root.innerHTML = `
    <i data-lucide="filter"></i>
    <span>Показаны курсы по направлениям: <strong>${escapeHtml(dirNames)}</strong>.
      Уровень до <strong>${escapeHtml(formatLevel(me.target_level || 'beginner'))}</strong>.
      <a href="/pages/profile.html?tab=preferences" class="link">Изменить программу →</a>
    </span>
  `;
  if (window.lucide) window.lucide.createIcons();
}

async function loadCourses() {
  const grid = document.getElementById('grid');
  grid.innerHTML = '<p class="muted">Загружаем…</p>';
  const query = {};
  const search = document.getElementById('search').value.trim();
  const level = document.getElementById('level').value;
  const cat = document.getElementById('category').value;
  const status = document.getElementById('status')?.value;
  if (search) query.search = search;
  if (level) query.level = level;
  if (cat) query.category_id = cat;
  if (status) query.status = status;

  try {
    const res = await coursesApi.list(query);
    if (!res.items.length) {
      mountEmpty(grid, {
        title: 'По вашему профилю курсов пока нет',
        description: me.role === 'student'
          ? 'Попробуйте изменить программу обучения в профиле'
          : 'Создайте первый курс через раздел «Преподавание»',
      });
      return;
    }
    grid.innerHTML = res.items.map(c => {
      const cat = categories.find(x => x.id === c.category_id);
      return `
        <a class="catalog-card" href="/pages/course.html?id=${c.id}">
          <div class="catalog-card__plate">
            <i data-lucide="${escapeHtml(cat?.icon_name || 'book-open')}"></i>
          </div>
          <div class="catalog-card__body">
            <div class="catalog-card__title">${escapeHtml(c.title)}</div>
            <div class="catalog-card__desc">${escapeHtml(c.short_description || c.description || '')}</div>
            <div class="catalog-card__meta">
              <span class="badge">${c.lessons_count} ${pluralize(c.lessons_count, ['урок', 'урока', 'уроков'])}</span>
              <span class="badge badge--primary">${escapeHtml(formatLevel(c.level))}</span>
              ${cat ? `<span class="badge">${escapeHtml(cat.name)}</span>` : ''}
            </div>
          </div>
        </a>
      `;
    }).join('');
    if (window.lucide) window.lucide.createIcons();
  } catch (err) {
    grid.innerHTML = `<p class="muted">Не удалось загрузить курсы. Попробуйте обновить страницу.</p>`;
    console.error('Catalog load failed:', err);
  }
}
