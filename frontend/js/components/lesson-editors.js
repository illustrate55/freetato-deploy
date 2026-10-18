// Редакторы контента уроков для teacher/admin: text / quiz / task.
// openLessonEditor(lesson, onSaved) — выбирает нужный редактор по lesson.type.

import { lessonsApi } from '../api/lessons.js';
import { quizzesApi } from '../api/quizzes.js';
import { tasksApi } from '../api/tasks.js';
import { openModal } from './modal.js';
import { toast } from './toast.js';
import { escapeHtml } from '../utils/dom.js';


export function openLessonEditor(lesson, onSaved) {
  if (lesson.type === 'text') return openTextEditor(lesson, onSaved);
  if (lesson.type === 'quiz') return openQuizEditor(lesson, onSaved);
  if (lesson.type === 'task') return openTaskEditor(lesson, onSaved);
  toast.error('Неизвестный тип урока: ' + lesson.type);
}


// ===== TEXT =====
function openTextEditor(lesson, onSaved) {
  const body = document.createElement('div');
  body.innerHTML = `
    <div class="form-group">
      <label class="form-label">Название</label>
      <input class="input" id="le-title" value="${escapeHtml(lesson.title)}">
    </div>
    <div class="form-group" style="max-width:200px">
      <label class="form-label">Длительность чтения, мин</label>
      <input type="number" class="input" id="le-dur" min="0" value="${lesson.duration_minutes || 0}">
    </div>
    <div class="le-text-grid">
      <div class="form-group">
        <label class="form-label">Содержание (Markdown)</label>
        <textarea class="textarea le-content" id="le-content">${escapeHtml(lesson.content_markdown || '')}</textarea>
      </div>
      <div class="form-group">
        <label class="form-label">Превью</label>
        <div class="le-preview" id="le-preview"></div>
      </div>
    </div>
  `;

  const footer = document.createElement('div');
  const cancel = document.createElement('button'); cancel.className = 'btn btn-ghost'; cancel.textContent = 'Отмена';
  const save = document.createElement('button'); save.className = 'btn btn-primary'; save.textContent = 'Сохранить';
  footer.append(cancel, save);

  const m = openModal({ title: 'Редактирование урока (текст)', body, footer, size: 'lg', closeOnOverlay: false });

  const ta = body.querySelector('#le-content');
  const preview = body.querySelector('#le-preview');
  function renderPreview() {
    const md = ta.value;
    preview.innerHTML = window.marked ? window.marked.parse(md, { sanitize: true }) : escapeHtml(md);
  }
  ta.addEventListener('input', renderPreview);
  renderPreview();

  cancel.addEventListener('click', m.close);
  save.addEventListener('click', async () => {
    save.disabled = true;
    try {
      await lessonsApi.update(lesson.id, {
        title: body.querySelector('#le-title').value.trim(),
        duration_minutes: parseInt(body.querySelector('#le-dur').value, 10) || 0,
        content_markdown: ta.value,
      });
      toast.success('Урок сохранён');
      m.close();
      onSaved && onSaved();
    } catch (err) {
      toast.error(err.message || 'Ошибка');
      save.disabled = false;
    }
  });
}


// ===== QUIZ =====
async function openQuizEditor(lesson, onSaved) {
  if (!lesson.quiz_id) { toast.error('У урока нет привязанного теста'); return; }

  let quiz;
  try {
    quiz = await quizzesApi.getFull(lesson.quiz_id);
  } catch (err) {
    toast.error(err.message || 'Не удалось загрузить тест');
    return;
  }

  const state = {
    title: quiz.title,
    description: quiz.description || '',
    passing_score: quiz.passing_score,
    max_attempts: quiz.max_attempts,
    questions: quiz.questions.map(q => ({
      text: q.text,
      type: q.type,
      points: q.points || 1,
      explanation: q.explanation || '',
      correct_text: q.correct_text || '',
      answers: (q.answers || []).map(a => ({ text: a.text, is_correct: !!a.is_correct })),
    })),
  };

  const body = document.createElement('div');
  body.innerHTML = `
    <div class="form-group">
      <label class="form-label">Название теста</label>
      <input class="input" id="q-title">
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div class="form-group">
        <label class="form-label">Проходной балл, %</label>
        <input type="number" class="input" id="q-pass" min="0" max="100">
      </div>
      <div class="form-group">
        <label class="form-label">Макс. попыток</label>
        <input type="number" class="input" id="q-max" min="1" max="20">
      </div>
    </div>
    <div class="le-questions" id="q-list"></div>
    <button class="btn btn-secondary mt-8" id="q-add">+ Добавить вопрос</button>
  `;

  const footer = document.createElement('div');
  const cancel = document.createElement('button'); cancel.className = 'btn btn-ghost'; cancel.textContent = 'Отмена';
  const save = document.createElement('button'); save.className = 'btn btn-primary'; save.textContent = 'Сохранить';
  footer.append(cancel, save);

  const m = openModal({ title: 'Редактирование теста', body, footer, size: 'lg', closeOnOverlay: false });

  body.querySelector('#q-title').value = state.title;
  body.querySelector('#q-pass').value = state.passing_score;
  body.querySelector('#q-max').value = state.max_attempts;

  function renderQuestions() {
    const list = body.querySelector('#q-list');
    list.innerHTML = state.questions.map((q, qi) => `
      <div class="le-question" data-q="${qi}">
        <div class="le-question__head">
          <strong>Вопрос ${qi + 1}</strong>
          <button class="btn btn-ghost btn-sm" data-del-q="${qi}">Удалить</button>
        </div>
        <div class="form-group">
          <label class="form-label">Текст вопроса</label>
          <input class="input" data-q-text="${qi}" value="${escapeHtml(q.text)}">
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
          <div class="form-group">
            <label class="form-label">Тип</label>
            <select class="select" data-q-type="${qi}">
              <option value="single" ${q.type === 'single' ? 'selected' : ''}>Один ответ</option>
              <option value="multiple" ${q.type === 'multiple' ? 'selected' : ''}>Несколько</option>
              <option value="text_short" ${q.type === 'text_short' ? 'selected' : ''}>Короткий текст</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Баллы</label>
            <input type="number" class="input" data-q-points="${qi}" min="1" value="${q.points}">
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Пояснение (показывается после ответа)</label>
          <input class="input" data-q-expl="${qi}" value="${escapeHtml(q.explanation || '')}">
        </div>
        ${q.type === 'text_short' ? `
          <div class="form-group">
            <label class="form-label">Эталонный ответ (без учёта регистра)</label>
            <input class="input" data-q-correct="${qi}" value="${escapeHtml(q.correct_text || '')}">
          </div>
        ` : `
          <div class="form-group">
            <label class="form-label">Варианты ответов</label>
            <div class="le-answers">
              ${q.answers.map((a, ai) => `
                <div class="le-answer">
                  <input type="${q.type === 'single' ? 'radio' : 'checkbox'}"
                         name="ans-${qi}"
                         data-a-correct="${qi}-${ai}"
                         ${a.is_correct ? 'checked' : ''}>
                  <input class="input" data-a-text="${qi}-${ai}" value="${escapeHtml(a.text)}">
                  <button class="btn btn-ghost btn-sm" data-del-a="${qi}-${ai}">×</button>
                </div>
              `).join('')}
            </div>
            <button class="btn btn-ghost btn-sm" data-add-a="${qi}">+ Вариант</button>
          </div>
        `}
      </div>
    `).join('') || '<p class="muted">Вопросов пока нет</p>';

    // Listeners
    list.querySelectorAll('[data-q-text]').forEach(el => {
      el.addEventListener('input', () => { state.questions[+el.dataset.qText].text = el.value; });
    });
    list.querySelectorAll('[data-q-type]').forEach(el => {
      el.addEventListener('change', () => {
        const qi = +el.dataset.qType;
        state.questions[qi].type = el.value;
        // Подстройка структуры
        if (el.value === 'text_short') {
          state.questions[qi].answers = [];
        } else if (state.questions[qi].answers.length === 0) {
          state.questions[qi].answers = [
            { text: '', is_correct: false },
            { text: '', is_correct: false },
          ];
        }
        renderQuestions();
      });
    });
    list.querySelectorAll('[data-q-points]').forEach(el => {
      el.addEventListener('input', () => { state.questions[+el.dataset.qPoints].points = parseInt(el.value, 10) || 1; });
    });
    list.querySelectorAll('[data-q-expl]').forEach(el => {
      el.addEventListener('input', () => { state.questions[+el.dataset.qExpl].explanation = el.value; });
    });
    list.querySelectorAll('[data-q-correct]').forEach(el => {
      el.addEventListener('input', () => { state.questions[+el.dataset.qCorrect].correct_text = el.value; });
    });
    list.querySelectorAll('[data-a-text]').forEach(el => {
      el.addEventListener('input', () => {
        const [qi, ai] = el.dataset.aText.split('-').map(Number);
        state.questions[qi].answers[ai].text = el.value;
      });
    });
    list.querySelectorAll('[data-a-correct]').forEach(el => {
      el.addEventListener('change', () => {
        const [qi, ai] = el.dataset.aCorrect.split('-').map(Number);
        const q = state.questions[qi];
        if (q.type === 'single') {
          q.answers.forEach((a, i) => a.is_correct = (i === ai));
        } else {
          q.answers[ai].is_correct = el.checked;
        }
      });
    });
    list.querySelectorAll('[data-del-q]').forEach(el => {
      el.addEventListener('click', () => {
        state.questions.splice(+el.dataset.delQ, 1);
        renderQuestions();
      });
    });
    list.querySelectorAll('[data-add-a]').forEach(el => {
      el.addEventListener('click', () => {
        state.questions[+el.dataset.addA].answers.push({ text: '', is_correct: false });
        renderQuestions();
      });
    });
    list.querySelectorAll('[data-del-a]').forEach(el => {
      el.addEventListener('click', () => {
        const [qi, ai] = el.dataset.delA.split('-').map(Number);
        state.questions[qi].answers.splice(ai, 1);
        renderQuestions();
      });
    });
  }

  body.querySelector('#q-add').addEventListener('click', () => {
    state.questions.push({
      text: '', type: 'single', points: 1, explanation: '', correct_text: '',
      answers: [
        { text: '', is_correct: true },
        { text: '', is_correct: false },
      ],
    });
    renderQuestions();
  });

  renderQuestions();

  cancel.addEventListener('click', m.close);
  save.addEventListener('click', async () => {
    // Также обновляем title урока, если изменился
    const title = body.querySelector('#q-title').value.trim();
    const passingScore = parseInt(body.querySelector('#q-pass').value, 10);
    const maxAttempts = parseInt(body.querySelector('#q-max').value, 10);

    // Валидация
    if (!title) { toast.error('Укажите название теста'); return; }
    if (!state.questions.length) { toast.error('Добавьте хотя бы один вопрос'); return; }
    for (const [i, q] of state.questions.entries()) {
      if (!q.text.trim()) { toast.error(`Вопрос ${i + 1}: укажите текст`); return; }
      if (q.type === 'text_short') {
        if (!(q.correct_text || '').trim()) { toast.error(`Вопрос ${i + 1}: укажите эталонный ответ`); return; }
      } else {
        if (q.answers.length < 2) { toast.error(`Вопрос ${i + 1}: минимум 2 варианта`); return; }
        if (!q.answers.some(a => a.is_correct)) { toast.error(`Вопрос ${i + 1}: отметьте хотя бы один правильный вариант`); return; }
        if (q.type === 'single' && q.answers.filter(a => a.is_correct).length !== 1) {
          toast.error(`Вопрос ${i + 1}: для типа «один ответ» отметьте ровно один правильный`);
          return;
        }
        for (const a of q.answers) {
          if (!a.text.trim()) { toast.error(`Вопрос ${i + 1}: пустой вариант ответа`); return; }
        }
      }
    }

    save.disabled = true;
    try {
      await quizzesApi.updateFull(lesson.quiz_id, {
        title,
        description: state.description || null,
        passing_score: passingScore,
        max_attempts: maxAttempts,
        shuffle_questions: false,
        show_correct_after: true,
        questions: state.questions.map(q => ({
          text: q.text.trim(),
          type: q.type,
          points: q.points,
          explanation: q.explanation || null,
          correct_text: q.type === 'text_short' ? q.correct_text.trim() : null,
          answers: q.type === 'text_short' ? [] : q.answers.map(a => ({
            text: a.text.trim(),
            is_correct: a.is_correct,
          })),
        })),
      });
      // Заодно обновим title урока (чтобы не расходился)
      if (lesson.title !== title) {
        try { await lessonsApi.update(lesson.id, { title }); } catch {}
      }
      toast.success('Тест сохранён');
      m.close();
      onSaved && onSaved();
    } catch (err) {
      toast.error(err.message || 'Ошибка сохранения');
      save.disabled = false;
    }
  });
}


// ===== TASK =====
async function openTaskEditor(lesson, onSaved) {
  if (!lesson.task_id) { toast.error('У урока нет привязанного задания'); return; }

  let task;
  try {
    task = await tasksApi.getFull(lesson.task_id);
  } catch (err) {
    toast.error(err.message || 'Не удалось загрузить задание');
    return;
  }

  const state = {
    title: task.title,
    description_md: task.description_md || '',
    task_type: task.task_type || 'code',
    language: task.language || 'python',
    requirements: [...(task.requirements || [])],
    hints: [...(task.hints || [])],
    check_criteria: (task.check_criteria || []).map(c => ({ criterion: c.criterion, weight: c.weight })),
    reference_solution: task.reference_solution || '',
    passing_score: task.passing_score,
  };

  const body = document.createElement('div');
  body.innerHTML = `
    <div class="form-group">
      <label class="form-label">Название</label>
      <input class="input" id="t-title">
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div class="form-group">
        <label class="form-label">Тип задания</label>
        <select class="select" id="t-type">
          <option value="code">code</option>
          <option value="theory">theory</option>
          <option value="mixed">mixed</option>
        </select>
      </div>
      <div class="form-group" id="t-lang-wrap">
        <label class="form-label">Язык программирования</label>
        <input class="input" id="t-lang">
      </div>
    </div>
    <div class="le-text-grid">
      <div class="form-group">
        <label class="form-label">Описание (Markdown)</label>
        <textarea class="textarea le-content" id="t-desc"></textarea>
      </div>
      <div class="form-group">
        <label class="form-label">Превью</label>
        <div class="le-preview" id="t-preview"></div>
      </div>
    </div>
    <div class="form-group">
      <label class="form-label">Требования (по одному в строке)</label>
      <textarea class="textarea" id="t-reqs" style="min-height:80px"></textarea>
    </div>
    <div class="form-group">
      <label class="form-label">Подсказки (по одной в строке)</label>
      <textarea class="textarea" id="t-hints" style="min-height:60px"></textarea>
    </div>
    <div class="form-group">
      <label class="form-label">Критерии проверки (сумма весов = 1.0)</label>
      <div id="t-criteria"></div>
      <button class="btn btn-ghost btn-sm mt-8" id="t-add-criterion">+ Критерий</button>
      <div class="form-hint" id="t-weights-hint"></div>
    </div>
    <div class="form-group">
      <label class="form-label">Эталонное решение</label>
      <textarea class="textarea input--mono" id="t-ref" style="min-height:140px"></textarea>
    </div>
    <div class="form-group" style="max-width:200px">
      <label class="form-label">Проходной балл, %</label>
      <input type="number" class="input" id="t-pass" min="0" max="100">
    </div>
  `;

  const footer = document.createElement('div');
  const cancel = document.createElement('button'); cancel.className = 'btn btn-ghost'; cancel.textContent = 'Отмена';
  const save = document.createElement('button'); save.className = 'btn btn-primary'; save.textContent = 'Сохранить';
  footer.append(cancel, save);

  const m = openModal({ title: 'Редактирование задания', body, footer, size: 'lg', closeOnOverlay: false });

  // Инициализация
  body.querySelector('#t-title').value = state.title;
  body.querySelector('#t-type').value = state.task_type;
  body.querySelector('#t-lang').value = state.language || '';
  body.querySelector('#t-desc').value = state.description_md;
  body.querySelector('#t-reqs').value = state.requirements.join('\n');
  body.querySelector('#t-hints').value = state.hints.join('\n');
  body.querySelector('#t-ref').value = state.reference_solution;
  body.querySelector('#t-pass').value = state.passing_score;

  function toggleLangWrap() {
    body.querySelector('#t-lang-wrap').classList.toggle('hidden', body.querySelector('#t-type').value !== 'code');
  }
  body.querySelector('#t-type').addEventListener('change', toggleLangWrap);
  toggleLangWrap();

  // Превью описания
  const desc = body.querySelector('#t-desc');
  const preview = body.querySelector('#t-preview');
  function renderPreview() {
    preview.innerHTML = window.marked ? window.marked.parse(desc.value, { sanitize: true }) : escapeHtml(desc.value);
  }
  desc.addEventListener('input', renderPreview);
  renderPreview();

  // Критерии
  function renderCriteria() {
    const root = body.querySelector('#t-criteria');
    root.innerHTML = state.check_criteria.map((c, i) => `
      <div class="le-criterion">
        <input class="input" data-cr-text="${i}" value="${escapeHtml(c.criterion)}" placeholder="Что проверяется">
        <input type="number" class="input" data-cr-w="${i}" step="0.05" min="0" max="1" value="${c.weight}" style="max-width:100px">
        <button class="btn btn-ghost btn-sm" data-del-cr="${i}">×</button>
      </div>
    `).join('') || '<p class="muted">Критериев нет</p>';

    root.querySelectorAll('[data-cr-text]').forEach(el => {
      el.addEventListener('input', () => { state.check_criteria[+el.dataset.crText].criterion = el.value; });
    });
    root.querySelectorAll('[data-cr-w]').forEach(el => {
      el.addEventListener('input', () => {
        state.check_criteria[+el.dataset.crW].weight = parseFloat(el.value) || 0;
        updateWeightsHint();
      });
    });
    root.querySelectorAll('[data-del-cr]').forEach(el => {
      el.addEventListener('click', () => {
        state.check_criteria.splice(+el.dataset.delCr, 1);
        renderCriteria();
        updateWeightsHint();
      });
    });
    updateWeightsHint();
  }

  function updateWeightsHint() {
    const sum = state.check_criteria.reduce((s, c) => s + (parseFloat(c.weight) || 0), 0);
    const hint = body.querySelector('#t-weights-hint');
    const ok = Math.abs(sum - 1) < 0.011;
    hint.textContent = `Сумма весов: ${sum.toFixed(2)}${ok ? ' ✓' : ' (должна быть 1.00)'}`;
    hint.style.color = ok ? 'var(--color-success)' : 'var(--color-error)';
  }

  body.querySelector('#t-add-criterion').addEventListener('click', () => {
    state.check_criteria.push({ criterion: '', weight: 0 });
    renderCriteria();
  });
  renderCriteria();

  cancel.addEventListener('click', m.close);
  save.addEventListener('click', async () => {
    const title = body.querySelector('#t-title').value.trim();
    const description_md = desc.value;
    const task_type = body.querySelector('#t-type').value;
    const language = body.querySelector('#t-lang').value.trim() || null;
    const passing_score = parseInt(body.querySelector('#t-pass').value, 10) || 70;
    const requirements = body.querySelector('#t-reqs').value.split('\n').map(s => s.trim()).filter(Boolean);
    const hints = body.querySelector('#t-hints').value.split('\n').map(s => s.trim()).filter(Boolean);
    const reference_solution = body.querySelector('#t-ref').value || null;
    const check_criteria = state.check_criteria
      .filter(c => c.criterion.trim())
      .map(c => ({ criterion: c.criterion.trim(), weight: parseFloat(c.weight) || 0 }));

    if (!title) { toast.error('Укажите название'); return; }
    if (description_md.trim().length < 20) { toast.error('Описание слишком короткое (минимум 20 символов)'); return; }
    if (!check_criteria.length) { toast.error('Добавьте хотя бы один критерий'); return; }
    const sum = check_criteria.reduce((s, c) => s + c.weight, 0);
    if (Math.abs(sum - 1) >= 0.011) { toast.error('Сумма весов критериев должна быть = 1.00'); return; }

    save.disabled = true;
    try {
      await tasksApi.update(lesson.task_id, {
        title,
        description_md,
        task_type,
        language: task_type === 'code' ? language : null,
        requirements,
        hints,
        check_criteria,
        reference_solution,
        passing_score,
      });
      // Sync title с уроком
      if (lesson.title !== title) {
        try { await lessonsApi.update(lesson.id, { title }); } catch {}
      }
      toast.success('Задание сохранено');
      m.close();
      onSaved && onSaved();
    } catch (err) {
      toast.error(err.message || 'Ошибка сохранения');
      save.disabled = false;
    }
  });
}
