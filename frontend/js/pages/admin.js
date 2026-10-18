import { mountHeader } from '../components/header.js';
import { mountSidebar } from '../components/sidebar.js';
import { usersApi, categoriesApi } from '../api/users.js';
import { coursesApi } from '../api/courses.js';
import { adminApi } from '../api/admin.js';
import { toast } from '../components/toast.js';
import { openModal, confirmModal, confirmDelete } from '../components/modal.js';
import { escapeHtml } from '../utils/dom.js';
import { formatDate } from '../utils/format.js';

let me = null;

document.addEventListener('DOMContentLoaded', async () => {
  me = await mountHeader('#header');
  if (!me) return;
  if (me.role !== 'admin') { location.replace('/pages/dashboard.html'); return; }
  mountSidebar('#sidebar', me);

  document.querySelectorAll('.tab').forEach(t => {
    t.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(x => x.classList.remove('is-active'));
      t.classList.add('is-active');
      renderTab(t.dataset.tab);
    });
  });
  renderTab('users');
});

async function renderTab(name) {
  const root = document.getElementById('tab-content');
  // Сразу показываем единый лоадер, чтобы при переключении между вкладками
  // не мелькали разные «промежуточные» состояния (пустой toolbar, одна
  // кнопка, чужие KPI). min-height фиксирует высоту, чтобы layout не «прыгал».
  root.innerHTML = '<p class="muted" style="padding:24px 0">Загружаем…</p>';
  if (name === 'users') return renderUsers(root);
  if (name === 'courses') return renderCourses(root);
  if (name === 'categories') return renderCategories(root);
  if (name === 'stats') return renderStats(root);
}

async function renderUsers(root) {
  root.innerHTML = `
    <div class="admin-toolbar">
      <input class="input" id="user-search" placeholder="Поиск по email или имени">
      <select class="select" id="role-filter" style="max-width:180px">
        <option value="">Все роли</option>
        <option value="student">Студент</option>
        <option value="teacher">Преподаватель</option>
        <option value="admin">Админ</option>
      </select>
      <button class="btn btn-primary" id="add-user-btn">+ Добавить</button>
    </div>
    <div id="users-table"><p class="muted">Загружаем…</p></div>
  `;
  let timer = null;
  document.getElementById('user-search').addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(load, 400);
  });
  document.getElementById('role-filter').addEventListener('change', load);
  document.getElementById('add-user-btn').addEventListener('click', addUserModal);

  async function load() {
    const q = {
      search: document.getElementById('user-search').value.trim() || undefined,
      role: document.getElementById('role-filter').value || undefined,
      page_size: 50,
    };
    const res = await usersApi.list(q);
    const tbl = document.getElementById('users-table');
    tbl.innerHTML = `
      <table class="table">
        <thead>
          <tr><th>Имя</th><th>Email</th><th>Роль</th><th>Статус</th><th></th></tr>
        </thead>
        <tbody>
          ${res.items.map(u => `
            <tr>
              <td>${escapeHtml(u.first_name)} ${escapeHtml(u.last_name)}</td>
              <td>${escapeHtml(u.email)}</td>
              <td>
                <select class="select" data-role="${u.id}" style="height:32px">
                  ${['student', 'teacher', 'admin'].map(r =>
                    `<option value="${r}" ${u.role === r ? 'selected' : ''}>${r}</option>`).join('')}
                </select>
              </td>
              <td>${u.is_blocked ? '<span class="badge badge--error">Заблокирован</span>' : '<span class="badge badge--success">Активен</span>'}</td>
              <td>
                <button class="btn btn-ghost btn-sm" data-toggle-block="${u.id}" data-blocked="${u.is_blocked}">${u.is_blocked ? 'Разблок.' : 'Заблок.'}</button>
                <button class="btn btn-ghost btn-sm" data-delete-user="${u.id}" data-name="${escapeHtml(u.email)}">Удалить</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
    tbl.querySelectorAll('[data-role]').forEach(sel => {
      const initialRole = sel.value;
      sel.addEventListener('change', async () => {
        // Выдача роли admin — важное действие, требует подтверждения
        if (sel.value === 'admin') {
          const ok = await confirmModal(
            'Назначить пользователю роль администратора? Он получит полный доступ к панели управления.',
            { title: 'Выдать админ-права', okText: 'Назначить', danger: true }
          );
          if (!ok) { sel.value = initialRole; return; }
        }
        try {
          await usersApi.changeRole(parseInt(sel.dataset.role, 10), sel.value);
          toast.success('Роль изменена');
        }
        catch (err) {
          sel.value = initialRole;
          toast.error(err.message || 'Ошибка');
        }
      });
    });
    tbl.querySelectorAll('[data-toggle-block]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const blocked = btn.dataset.blocked === 'true';
        try {
          await usersApi.update(parseInt(btn.dataset.toggleBlock, 10), { is_blocked: !blocked });
          toast.success('Статус изменён');
          load();
        } catch (err) { toast.error(err.message || 'Ошибка'); }
      });
    });
    tbl.querySelectorAll('[data-delete-user]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const ok = await confirmDelete(btn.dataset.name || 'пользователя');
        if (!ok) return;
        try { await usersApi.remove(parseInt(btn.dataset.deleteUser, 10)); toast.success('Сохранено'); load(); }
        catch (err) { toast.error(err.message || 'Ошибка'); }
      });
    });
  }
  load();
}

function addUserModal() {
  const body = document.createElement('div');
  body.innerHTML = `
    <div class="form-group"><label class="form-label">Email</label><input type="email" class="input" id="u-email"></div>
    <div class="form-group"><label class="form-label">Пароль</label><input type="password" class="input" id="u-pwd"></div>
    <div class="form-group"><label class="form-label">Имя</label><input class="input" id="u-first"></div>
    <div class="form-group"><label class="form-label">Фамилия</label><input class="input" id="u-last"></div>
    <div class="form-group">
      <label class="form-label">Роль</label>
      <select class="select" id="u-role">
        <option value="student">Студент</option>
        <option value="teacher">Преподаватель</option>
        <option value="admin">Админ</option>
      </select>
    </div>
  `;
  const footer = document.createElement('div');
  const cancel = document.createElement('button'); cancel.className = 'btn btn-ghost'; cancel.textContent = 'Отмена';
  const save = document.createElement('button'); save.className = 'btn btn-primary'; save.textContent = 'Создать';
  footer.append(cancel, save);
  const m = openModal({ title: 'Новый пользователь', body, footer });
  cancel.addEventListener('click', m.close);
  save.addEventListener('click', async () => {
    try {
      await usersApi.create({
        email: body.querySelector('#u-email').value.trim(),
        password: body.querySelector('#u-pwd').value,
        first_name: body.querySelector('#u-first').value.trim(),
        last_name: body.querySelector('#u-last').value.trim(),
        role: body.querySelector('#u-role').value,
      });
      m.close();
      toast.success('Создан');
      renderTab('users');
    } catch (err) { toast.error(err.message || 'Ошибка'); }
  });
}

async function renderCourses(root) {
  root.innerHTML = '<p class="muted">Загружаем…</p>';
  const res = await coursesApi.list({ page_size: 100 });
  root.innerHTML = `
    <table class="table">
      <thead><tr><th>Название</th><th>Автор</th><th>Уровень</th><th>Статус</th><th></th></tr></thead>
      <tbody>
        ${res.items.map(c => `
          <tr>
            <td><a class="link" href="/pages/course.html?id=${c.id}">${escapeHtml(c.title)}</a></td>
            <td>#${c.author_id || '—'}</td>
            <td>${escapeHtml(c.level)}</td>
            <td>${escapeHtml(c.status)}</td>
            <td>
              <button class="btn btn-ghost btn-sm" data-archive="${c.id}">Архив</button>
              <button class="btn btn-danger btn-sm" data-delete-course="${c.id}" data-name="${escapeHtml(c.title)}">Удалить</button>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
  root.querySelectorAll('[data-archive]').forEach(btn => {
    btn.addEventListener('click', async () => {
      try { await coursesApi.archive(parseInt(btn.dataset.archive, 10)); toast.success('Архивирован'); renderCourses(root); }
      catch (err) { toast.error(err.message || 'Ошибка'); }
    });
  });
  root.querySelectorAll('[data-delete-course]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const ok = await confirmDelete(btn.dataset.name || 'курс');
      if (!ok) return;
      try { await coursesApi.remove(parseInt(btn.dataset.deleteCourse, 10)); toast.success('Сохранено'); renderCourses(root); }
      catch (err) { toast.error(err.message || 'Ошибка'); }
    });
  });
}

async function renderCategories(root) {
  root.innerHTML = `
    <button class="btn btn-primary mb-16" id="add-cat">+ Добавить</button>
    <div id="cat-list"><p class="muted">Загружаем…</p></div>
  `;
  document.getElementById('add-cat').addEventListener('click', addCategoryModal);
  const list = await categoriesApi.list();
  document.getElementById('cat-list').innerHTML = `
    <table class="table">
      <thead><tr><th>Название</th><th>Slug</th><th>Иконка</th><th></th></tr></thead>
      <tbody>
        ${list.map(c => `
          <tr>
            <td>${escapeHtml(c.name)}</td>
            <td>${escapeHtml(c.slug)}</td>
            <td>${escapeHtml(c.icon_name || '—')}</td>
            <td><button class="btn btn-danger btn-sm" data-delete-cat="${c.id}" data-name="${escapeHtml(c.name)}">Удалить</button></td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
  document.querySelectorAll('[data-delete-cat]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const ok = await confirmDelete(btn.dataset.name || 'категорию');
      if (!ok) return;
      try { await categoriesApi.remove(parseInt(btn.dataset.deleteCat, 10)); toast.success('Сохранено'); renderCategories(root); }
      catch (err) { toast.error(err.message || 'Ошибка'); }
    });
  });
}

function addCategoryModal() {
  const body = document.createElement('div');
  body.innerHTML = `
    <div class="form-group"><label class="form-label">Название</label><input class="input" id="c-name"></div>
    <div class="form-group"><label class="form-label">Slug</label><input class="input" id="c-slug"></div>
    <div class="form-group"><label class="form-label">Имя иконки (Lucide)</label><input class="input" id="c-icon" placeholder="например, Server"></div>
  `;
  const footer = document.createElement('div');
  const cancel = document.createElement('button'); cancel.className = 'btn btn-ghost'; cancel.textContent = 'Отмена';
  const save = document.createElement('button'); save.className = 'btn btn-primary'; save.textContent = 'Создать';
  footer.append(cancel, save);
  const m = openModal({ title: 'Новая категория', body, footer });
  cancel.addEventListener('click', m.close);
  save.addEventListener('click', async () => {
    try {
      await categoriesApi.create({
        name: body.querySelector('#c-name').value.trim(),
        slug: body.querySelector('#c-slug').value.trim(),
        icon_name: body.querySelector('#c-icon').value.trim() || null,
      });
      m.close(); toast.success('Создана'); renderTab('categories');
    } catch (err) { toast.error(err.message || 'Ошибка'); }
  });
}

async function renderStats(root) {
  root.innerHTML = '<p class="muted">Загружаем…</p>';
  try {
    const s = await adminApi.stats();
    root.innerHTML = `
      <div class="admin-stats">
        <div class="kpi-card"><div class="kpi-card__label">Всего пользователей</div><div class="kpi-card__value">${s.users_total}</div></div>
        <div class="kpi-card"><div class="kpi-card__label">Студентов</div><div class="kpi-card__value">${s.users_students}</div></div>
        <div class="kpi-card"><div class="kpi-card__label">Преподавателей</div><div class="kpi-card__value">${s.users_teachers}</div></div>
        <div class="kpi-card"><div class="kpi-card__label">Опубликованных курсов</div><div class="kpi-card__value">${s.courses_published}</div></div>
        <div class="kpi-card"><div class="kpi-card__label">Попыток тестов</div><div class="kpi-card__value">${s.quiz_attempts_total}</div></div>
        <div class="kpi-card"><div class="kpi-card__label">ИИ-токенов за 30 дней</div><div class="kpi-card__value">${s.ai_tokens_month.toLocaleString('ru-RU')}</div></div>
      </div>
    `;
  } catch (err) {
    root.innerHTML = `<p class="muted">${escapeHtml(err.message || '')}</p>`;
  }
}
