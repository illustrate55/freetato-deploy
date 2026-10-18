// Empty state со спящим динозавриком (анимация First ↔ Second через 600мс).

import { escapeHtml } from '../utils/dom.js';

let animationStarted = false;

function startAnimation() {
  if (animationStarted) return;
  animationStarted = true;
  setInterval(() => {
    document.querySelectorAll('.empty-state__dino[data-frame-second]').forEach((img) => {
      const second = img.dataset.frameSecond;
      const original = img.dataset.frameFirst;
      if (!second || !original) return;
      img.src = img.src.endsWith(second) ? original : second;
    });
  }, 600);
}

export function mountEmpty(root, { title, description, actionText, actionHref, onAction } = {}) {
  const first = '/assets/img/dino/dinoSleepFirst.png';
  const second = '/assets/img/dino/dinoSleepSecond.png';
  const html = `
    <div class="empty-state">
      <img class="empty-state__dino"
           src="${first}"
           data-frame-first="${first}"
           data-frame-second="${second}"
           alt="">
      <h3 class="empty-state__title">${escapeHtml(title || 'Пока ничего нет')}</h3>
      ${description ? `<p class="empty-state__text">${escapeHtml(description)}</p>` : ''}
      ${actionText ? `<a class="btn btn-primary" ${actionHref ? `href="${escapeHtml(actionHref)}"` : ''}>${escapeHtml(actionText)}</a>` : ''}
    </div>
  `;
  if (typeof root === 'string') root = document.querySelector(root);
  if (!root) return;
  root.innerHTML = html;
  if (onAction) {
    root.querySelector('.btn')?.addEventListener('click', (e) => {
      e.preventDefault();
      onAction();
    });
  }
  startAnimation();
}
