import { mountHeader } from '../components/header.js';
import { tasksApi, submissionsApi } from '../api/tasks.js';
import { toast } from '../components/toast.js';
import { escapeHtml, getQueryParam } from '../utils/dom.js';

let me = null;
let taskId = null;
let courseId = null;
let task = null;
let runFrameToggle = false;
let runInterval = null;

document.addEventListener('DOMContentLoaded', async () => {
  me = await mountHeader('#header');
  if (!me) return;
  taskId = parseInt(getQueryParam('id'), 10);
  courseId = parseInt(getQueryParam('course'), 10) || null;

  try {
    task = await tasksApi.get(taskId);
  } catch (err) {
    document.getElementById('content').innerHTML = `<p class="muted">${escapeHtml(err.message || '')}</p>`;
    return;
  }
  renderTask();
});

function renderTask() {
  const descHtml = window.marked ? window.marked.parse(task.description_md, { sanitize: true }) : escapeHtml(task.description_md);
  const reqHtml = (task.requirements || []).map(r => `<li>${escapeHtml(r)}</li>`).join('');

  document.getElementById('content').innerHTML = `
    <div class="task-layout">
      <div class="task-condition">
        <h1>${escapeHtml(task.title)}</h1>
        <div class="task-condition__body">${descHtml}</div>
        ${reqHtml ? `<h3 class="mt-16 mb-8">Требования</h3><ul>${reqHtml}</ul>` : ''}
        ${task.hints?.length ? `
          <details class="task-condition__hints">
            <summary>Подсказки (${task.hints.length})</summary>
            ${task.hints.map(h => `<div class="task-condition__hint">${escapeHtml(h)}</div>`).join('')}
          </details>
        ` : ''}
      </div>
      <div class="task-solution">
        <h3 class="mb-8">Ваше решение</h3>
        <textarea id="solution" class="task-solution__textarea" placeholder="Напишите ваше решение здесь…"></textarea>
        <div class="task-solution__counter">
          <span id="counter">0 / ${task.max_solution_length}</span>
          <button class="btn btn-primary" id="submit-btn">Отправить на проверку</button>
        </div>
      </div>
    </div>
    <div id="result-area"></div>
  `;

  const ta = document.getElementById('solution');
  const counter = document.getElementById('counter');
  ta.addEventListener('input', () => {
    counter.textContent = `${ta.value.length} / ${task.max_solution_length}`;
  });
  document.getElementById('submit-btn').addEventListener('click', () => submit(ta.value));
}

async function submit(solution) {
  if (!solution.trim()) {
    toast.error('Напишите решение');
    return;
  }
  document.getElementById('submit-btn').disabled = true;
  showLoader();
  try {
    const res = await tasksApi.submit(taskId, solution);
    // Если ИИ не настроен — backend сразу вернёт status='error' без поллинга.
    if (res.status === 'error') {
      const sub = await submissionsApi.get(res.submission_id);
      hideLoader();
      renderResult(sub);
      return;
    }
    pollSubmission(res.submission_id);
  } catch (err) {
    hideLoader();
    document.getElementById('submit-btn').disabled = false;
    toast.error(err.message || 'Не удалось отправить');
  }
}

function showLoader() {
  document.getElementById('result-area').innerHTML = `
    <div class="task-loader">
      <h3>Идёт проверка ИИ</h3>
      <p class="muted">Это может занять до минуты…</p>
      <div class="task-loader__road">
        <img class="task-loader__dino" id="run-dino" src="/assets/img/dino/dinoRunFirst.png" alt="">
        <img class="task-loader__cactus" src="/assets/img/dino/kaktusRoad.png" alt="">
      </div>
    </div>
  `;
  if (runInterval) clearInterval(runInterval);
  runInterval = setInterval(() => {
    runFrameToggle = !runFrameToggle;
    const img = document.getElementById('run-dino');
    if (img) img.src = runFrameToggle
      ? '/assets/img/dino/dinoRunSecond.png'
      : '/assets/img/dino/dinoRunFirst.png';
  }, 100);
}

function hideLoader() {
  if (runInterval) { clearInterval(runInterval); runInterval = null; }
  document.getElementById('result-area').innerHTML = '';
}

async function pollSubmission(id) {
  const start = Date.now();
  const tick = async () => {
    let sub;
    try {
      sub = await submissionsApi.get(id);
    } catch (err) {
      hideLoader();
      toast.error(err.message || 'Ошибка');
      return;
    }
    if (sub.status === 'checked' || sub.status === 'error') {
      hideLoader();
      renderResult(sub);
      return;
    }
    if (Date.now() - start > 120000) {
      hideLoader();
      toast.error('Превышено время ожидания (2 минуты)');
      return;
    }
    setTimeout(tick, 2000);
  };
  tick();
}

function renderResult(sub) {
  if (sub.status === 'error') {
    document.getElementById('result-area').innerHTML = `
      <div class="task-result">
        <h3>Ошибка проверки</h3>
        <p class="muted">${escapeHtml(sub.error_message || '')}</p>
      </div>
    `;
    document.getElementById('submit-btn').disabled = false;
    return;
  }

  const passed = sub.is_passed;
  const criteriaHtml = (sub.ai_per_criterion || []).map(c => `
    <tr>
      <td>${escapeHtml(c.criterion || '')}</td>
      <td>${Math.round((c.score || 0) * 100)}%</td>
      <td>${escapeHtml(c.comment || '')}</td>
    </tr>
  `).join('');
  const tipsHtml = (sub.ai_improvement_tips || []).map(t => `<li>${escapeHtml(t)}</li>`).join('');

  document.getElementById('result-area').innerHTML = `
    <div class="task-result">
      <div class="task-result__head">
        <div class="task-result__score">${sub.score_percent ?? 0}%</div>
        <div class="${passed ? 'badge badge--success' : 'badge badge--error'}" style="height:28px">
          ${passed ? '✓ Сдано' : '✗ Не сдано'}
        </div>
      </div>
      ${sub.ai_summary ? `<p>${escapeHtml(sub.ai_summary)}</p>` : ''}
      ${criteriaHtml ? `
        <table class="task-result__criteria-table">
          <thead><tr><th>Критерий</th><th>Балл</th><th>Комментарий</th></tr></thead>
          <tbody>${criteriaHtml}</tbody>
        </table>
      ` : ''}
      ${tipsHtml ? `<h4 class="mt-16 mb-8">Советы</h4><ul>${tipsHtml}</ul>` : ''}
      <div class="mt-16">
        <a class="btn btn-primary" href="${courseId ? `/pages/course.html?id=${courseId}` : '/pages/dashboard.html'}">К курсу</a>
        <button class="btn btn-secondary" id="retry-btn">Попробовать снова</button>
      </div>
    </div>
  `;
  document.getElementById('retry-btn').addEventListener('click', () => {
    document.getElementById('result-area').innerHTML = '';
    document.getElementById('submit-btn').disabled = false;
  });
}
