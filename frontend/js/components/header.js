// Sticky header с логотипом-динозавром и меню пользователя.

import { authApi } from '../api/auth.js';
import { usersApi } from '../api/users.js';
import { logoutClient } from '../api/client.js';
import { initials } from '../utils/format.js';
import { escapeHtml } from '../utils/dom.js';

function readCachedUser() {
  try {
    const raw = sessionStorage.getItem('user');
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

function renderHeader(root, user) {
  const ini = initials(user.first_name, user.last_name);
  const fullName = `${user.first_name} ${user.last_name}`.trim();

  const homeHref = user.role === 'admin' ? '/pages/admin.html' : '/pages/dashboard.html';
  root.className = 'app-header';
  root.innerHTML = `
    <a class="app-header__brand" href="${homeHref}">
      <img src="/assets/img/dino/icon.png" alt="">
      <span>FREETATO ДПО</span>
    </a>
    <div class="app-header__spacer"></div>
    <div class="app-header__user">
      <button class="app-header__user-btn" id="user-menu-btn">
        <span class="avatar avatar--sm">${escapeHtml(ini)}</span>
        <span>${escapeHtml(fullName)}</span>
      </button>
      <div class="app-header__menu hidden" id="user-menu">
        <a href="/pages/profile.html">Профиль</a>
        <button id="user-logout">Выйти</button>
      </div>
    </div>
  `;

  const btn = root.querySelector('#user-menu-btn');
  const menu = root.querySelector('#user-menu');
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    menu.classList.toggle('hidden');
  });
  document.addEventListener('click', () => menu.classList.add('hidden'));

  root.querySelector('#user-logout').addEventListener('click', async () => {
    try { await authApi.logout(); } catch {}
    logoutClient();
    location.replace('/pages/login.html');
  });
}

// Фоновая ревалидация — обновляет кэшированный user через /me.
// Если роль изменилась — перезагружаем страницу, чтобы пересобрать sidebar и
// фильтры по роли консистентно.
async function revalidateInBackground(root, cached) {
  try {
    const user = await usersApi.me();
    sessionStorage.setItem('user', JSON.stringify(user));
    if (!cached) { renderHeader(root, user); return; }
    const nameChanged = cached.first_name !== user.first_name
      || cached.last_name !== user.last_name;
    if (nameChanged) renderHeader(root, user);
    if (cached.role !== user.role) location.reload();
  } catch {
    sessionStorage.removeItem('user');
    location.replace('/pages/login.html');
  }
}

export async function mountHeader(selector) {
  const root = typeof selector === 'string' ? document.querySelector(selector) : selector;
  if (!root) return null;

  // Оптимистичный путь: профиль закэширован после login/register —
  // отдаём страницу мгновенно и проверяем /me фоном (не блокируем рендер).
  const cached = readCachedUser();
  if (cached) {
    renderHeader(root, cached);
    revalidateInBackground(root, cached);
    return cached;
  }

  // Кэша нет (например, открыли страницу в новой вкладке) — ждём /me синхронно.
  let user = null;
  try {
    user = await usersApi.me();
  } catch {
    sessionStorage.removeItem('user');
    location.replace('/pages/login.html');
    return null;
  }
  sessionStorage.setItem('user', JSON.stringify(user));
  renderHeader(root, user);
  return user;
}
