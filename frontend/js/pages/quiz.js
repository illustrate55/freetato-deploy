import { mountHeader } from '../components/header.js';
import { quizzesApi, attemptsApi } from '../api/quizzes.js';
import { toast } from '../components/toast.js';
import { escapeHtml, getQueryParam } from '../utils/dom.js';

const BONUS_DINOS = ['/assets/img/dino/dinoBonus.png', '/assets/img/dino/dinoBonus2.png', '/assets/img/dino/dinoBonus3.png'];

let me = null;
let quizId = null;
let courseId = null;
let quiz = null;
let attemptId = null;
let answers = {}; // { question_id: { selected_answer_ids: [], answer_text: '' } }
let currentIdx = 0;
let result = null;

document.addEventListener('DOMContentLoaded', async () => {
  me = await mountHeader('#header');
  if (!me) return;
  quizId = parseInt(getQueryParam('id'), 10);
  courseId = parseInt(getQueryParam('course'), 10) || null;

  try {
    quiz = await quizzesApi.get(quizId);
  } catch (err) {
    document.getElementById('content').innerHTML = `<p class="muted">${escapeHtml(err.message || '')}</p>`;
    return;
  }
  renderStart();
});

function renderStart() {
  document.getElementById('content').innerHTML = `
    <div class="quiz-card">
      <h1 class="mb-16">${escapeHtml(quiz.title)}</h1>
      <p class="muted mb-16">
        Вопросов: ${quiz.questions.length}.
        Проходной балл: ${quiz.passing_score}%.
        Попыток: до ${quiz.max_attempts}.
      </p>
      <button class="btn btn-primary btn-lg" id="start-btn">Начать тест</button>
    </div>
  `;
  document.getElementById('start-btn').addEventListener('click', startAttempt);
}

async function startAttempt() {
  try {
    const res = await quizzesApi.startAttempt(quizId);
    attemptId = res.attempt_id;
    answers = {};
    currentIdx = 0;
    renderQuestion();
  } catch (err) {
    toast.error(err.message || 'Не удалось начать');
  }
}

function renderQuestion() {
  const q = quiz.questions[currentIdx];
  const selected = answers[q.id]?.selected_answer_ids || [];
  const textValue = answers[q.id]?.answer_text || '';

  let answersHtml = '';
  if (q.type === 'single' || q.type === 'multiple') {
    const inputType = q.type === 'single' ? 'radio' : 'checkbox';
    answersHtml = `
      <div class="quiz__answers">
        ${q.answers.map(a => `
          <label class="quiz__answer ${selected.includes(a.id) ? 'is-active' : ''}">
            <input type="${inputType}" name="ans" value="${a.id}" ${selected.includes(a.id) ? 'checked' : ''}>
            <span>${escapeHtml(a.text)}</span>
          </label>
        `).join('')}
      </div>
    `;
  } else if (q.type === 'text_short') {
    answersHtml = `
      <input type="text" class="input" id="text-answer" placeholder="Введите ответ" value="${escapeHtml(textValue)}">
    `;
  }

  document.getElementById('content').innerHTML = `
    <div class="quiz-card">
      <div class="quiz__progress">Вопрос ${currentIdx + 1} из ${quiz.questions.length}</div>
      <div class="quiz__question">${escapeHtml(q.text)}</div>
      ${answersHtml}
      <div class="quiz__nav">
        <button class="btn btn-ghost" id="prev-btn" ${currentIdx === 0 ? 'disabled' : ''}>← Назад</button>
        ${currentIdx < quiz.questions.length - 1
          ? `<button class="btn btn-primary" id="next-btn">Далее →</button>`
          : `<button class="btn btn-primary" id="finish-btn">Завершить тест</button>`}
      </div>
    </div>
  `;

  // Слушатели на ответы
  document.querySelectorAll('input[name="ans"]').forEach(inp => {
    inp.addEventListener('change', () => {
      const checked = Array.from(document.querySelectorAll('input[name="ans"]:checked')).map(i => parseInt(i.value, 10));
      answers[q.id] = { selected_answer_ids: checked, answer_text: null };
      document.querySelectorAll('.quiz__answer').forEach(l => {
        const inp2 = l.querySelector('input');
        l.classList.toggle('is-active', checked.includes(parseInt(inp2.value, 10)));
      });
    });
  });
  document.getElementById('text-answer')?.addEventListener('input', (e) => {
    answers[q.id] = { selected_answer_ids: [], answer_text: e.target.value };
  });
  document.getElementById('prev-btn')?.addEventListener('click', () => { currentIdx--; renderQuestion(); });
  document.getElementById('next-btn')?.addEventListener('click', () => { currentIdx++; renderQuestion(); });
  document.getElementById('finish-btn')?.addEventListener('click', submitAttempt);
}

async function submitAttempt() {
  const btn = document.getElementById('finish-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Отправка…'; }
  const payload = quiz.questions.map(q => ({
    question_id: q.id,
    selected_answer_ids: answers[q.id]?.selected_answer_ids || [],
    answer_text: answers[q.id]?.answer_text || null,
  }));
  try {
    result = await attemptsApi.submit(attemptId, payload);
    renderResult();
  } catch (err) {
    toast.error(err.message || 'Ошибка отправки');
    if (btn) { btn.disabled = false; btn.textContent = 'Завершить'; }
  }
}

function renderResult() {
  const passed = result.passed;
  const bonusImg = passed ? BONUS_DINOS[Math.floor(Math.random() * BONUS_DINOS.length)] : null;

  const head = `
    <div class="quiz-result__head">
      ${bonusImg ? `<img class="quiz-result__bonus" src="${bonusImg}" alt="">` : ''}
      <div class="quiz-result__score">${result.score} из ${result.max_score}</div>
      <div class="quiz-result__percent">${result.score_percent}% — ${passed ? 'Тест пройден ✓' : 'Не пройден'}</div>
    </div>
  `;
  const items = result.answers.map((a, idx) => {
    const q = quiz.questions[idx];
    return `
      <div class="quiz-result__item ${a.is_correct ? 'is-correct' : 'is-wrong'}">
        <strong>${idx + 1}. ${escapeHtml(q.text)}</strong>
        <div style="margin-top:6px">${a.is_correct ? '✓ Верно' : '✗ Неверно'} · ${a.points_awarded} баллов</div>
        ${a.explanation ? `<div class="quiz-result__explanation">${escapeHtml(a.explanation)}</div>` : ''}
      </div>
    `;
  }).join('');

  document.getElementById('content').innerHTML = `
    <div class="quiz-card">
      ${head}
      <div class="quiz-result__items">${items}</div>
      <div class="quiz__nav mt-24">
        <a class="btn btn-ghost" href="${courseId ? `/pages/course.html?id=${courseId}` : '/pages/dashboard.html'}">К курсу</a>
        <button class="btn btn-secondary" id="retry-btn">Пройти ещё раз</button>
      </div>
    </div>
  `;
  document.getElementById('retry-btn').addEventListener('click', startAttempt);
}
