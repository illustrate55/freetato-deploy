// Sidebar с навигацией. Меню зависит от роли.

const ITEMS = [
  { href: '/pages/dashboard.html', label: 'Главная', icon: 'home', roles: ['student', 'teacher'] },
  { href: '/pages/catalog.html', label: 'Каталог', icon: 'book-open', roles: ['student', 'teacher'] },
  { href: '/pages/profile.html?tab=courses', label: 'Мои курсы', icon: 'graduation-cap', roles: ['student'] },
  { href: '/pages/teacher.html', label: 'Преподавание', icon: 'edit-3', roles: ['teacher'] },
  { href: '/pages/admin.html', label: 'Админ-панель', icon: 'shield', roles: ['admin'] },
];

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

export function mountSidebar(selector, user, currentPath = location.pathname) {
  const root = typeof selector === 'string' ? document.querySelector(selector) : selector;
  if (!root || !user) return;

  root.className = 'app-sidebar';
  const html = ITEMS
    .filter(it => !it.roles || it.roles.includes(user.role))
    .map(it => {
      const isActive = currentPath === it.href.split('?')[0];
      return `
        <a class="app-sidebar__item ${isActive ? 'is-active' : ''}" href="${escapeHtml(it.href)}">
          <i data-lucide="${it.icon}" style="width:18px;height:18px"></i>
          <span>${escapeHtml(it.label)}</span>
        </a>
      `;
    })
    .join('');
  root.innerHTML = html;

  if (window.lucide) window.lucide.createIcons();
}
