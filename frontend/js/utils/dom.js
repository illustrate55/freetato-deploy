// Утилиты для DOM.

/** Безопасный выбор элемента. Бросает если не найден. */
export function $(selector, root = document) {
  const el = root.querySelector(selector);
  if (!el) throw new Error(`Не найден элемент: ${selector}`);
  return el;
}

export function $$(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

/** Экранирование HTML — для безопасной вставки пользовательских строк. */
export function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** Установить текст в элемент по селектору. */
export function setText(selector, text, root = document) {
  const el = root.querySelector(selector);
  if (el) el.textContent = text ?? '';
}

/** Сборка query string из объекта. */
export function getQueryParam(name) {
  return new URLSearchParams(location.search).get(name);
}

/** Сделать элемент скрытым/видимым. */
export function show(el) { el.classList.remove('hidden'); }
export function hide(el) { el.classList.add('hidden'); }
