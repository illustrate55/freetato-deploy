// Универсальная модалка. openModal({ title, body, footer, size, onClose }).

export function openModal({ title = '', body = '', footer = '', size = 'md', onClose, closeOnOverlay = true } = {}) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';

  const modal = document.createElement('div');
  modal.className = 'modal' + (size === 'lg' ? ' modal--lg' : '');
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');

  const header = document.createElement('div');
  header.className = 'modal__header';
  header.innerHTML = `
    <div class="modal__title"></div>
    <button class="modal__close" aria-label="Закрыть">×</button>
  `;
  header.querySelector('.modal__title').textContent = title;

  const bodyEl = document.createElement('div');
  bodyEl.className = 'modal__body';
  if (typeof body === 'string') bodyEl.innerHTML = body;
  else if (body instanceof Node) bodyEl.appendChild(body);

  const footerEl = document.createElement('div');
  footerEl.className = 'modal__footer';
  if (typeof footer === 'string') footerEl.innerHTML = footer;
  else if (footer instanceof Node) footerEl.appendChild(footer);

  modal.appendChild(header);
  modal.appendChild(bodyEl);
  if (footer) modal.appendChild(footerEl);
  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  const onKey = (e) => {
    if (e.key === 'Escape') close();
  };
  document.addEventListener('keydown', onKey);

  const close = () => {
    document.removeEventListener('keydown', onKey);
    overlay.remove();
    if (onClose) onClose();
  };

  header.querySelector('.modal__close').addEventListener('click', close);
  if (closeOnOverlay) {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) close();
    });
  }

  return { overlay, modal, body: bodyEl, footer: footerEl, close };
}

export function confirmModal(message, { title = 'Подтверждение', okText = 'OK', cancelText = 'Отмена', danger = false } = {}) {
  return new Promise((resolve) => {
    const footer = document.createElement('div');
    footer.style.display = 'flex';
    footer.style.gap = '12px';
    const cancel = document.createElement('button');
    cancel.className = 'btn btn-ghost';
    cancel.textContent = cancelText;
    const ok = document.createElement('button');
    ok.className = 'btn ' + (danger ? 'btn-danger' : 'btn-primary');
    ok.textContent = okText;
    footer.appendChild(cancel);
    footer.appendChild(ok);

    // Экранирование на случай пользовательских имён в message
    const p = document.createElement('p');
    p.textContent = message;
    // Резолвим ДО m.close(), потому что m.close() триггерит onClose,
    // который пытается resolve(false) — и если бы мы вызывали resolve после close,
    // OK всегда сводился бы к false (Promise идемпотентен по первому resolve).
    const m = openModal({ title, body: p, footer, onClose: () => resolve(false) });
    cancel.addEventListener('click', () => { resolve(false); m.close(); });
    ok.addEventListener('click', () => { resolve(true); m.close(); });
  });
}

// Хелпер для подтверждения удаления — стандартное сообщение и красная кнопка.
export function confirmDelete(name) {
  return confirmModal(`Вы уверены, что хотите удалить «${name}»?`, {
    title: 'Удалить',
    okText: 'Удалить',
    cancelText: 'Отмена',
    danger: true,
  });
}
