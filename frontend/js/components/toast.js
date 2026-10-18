// Тосты-уведомления. Авто-скрытие через 3 сек.

let container = null;

function ensureContainer() {
  if (container && document.body.contains(container)) return container;
  container = document.createElement('div');
  container.className = 'toast-container';
  document.body.appendChild(container);
  return container;
}

function escape(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

const MAX_TOASTS = 3;

export function showToast(message, type = 'info', timeout = 3000) {
  const root = ensureContainer();
  // Не копим больше MAX_TOASTS — удаляем самые старые
  while (root.children.length >= MAX_TOASTS) {
    root.firstChild?.remove();
  }
  const t = document.createElement('div');
  t.className = `toast toast--${type}`;
  t.setAttribute('role', type === 'error' ? 'alert' : 'status');
  t.innerHTML = `<div>${escape(message)}</div>`;
  // Клик по тосту скрывает его сразу — на случай если их много
  t.addEventListener('click', () => t.remove());
  root.appendChild(t);
  setTimeout(() => {
    t.style.opacity = '0';
    setTimeout(() => t.remove(), 200);
  }, timeout);
}

export const toast = {
  info:    (m) => showToast(m, 'info'),
  success: (m) => showToast(m, 'success'),
  error:   (m) => showToast(m, 'error'),
  warning: (m) => showToast(m, 'warning'),
};
