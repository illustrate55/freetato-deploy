import { mountHeader } from '../components/header.js';
import { mountSidebar } from '../components/sidebar.js';
import { coursesApi, modulesApi } from '../api/courses.js';
import { categoriesApi } from '../api/users.js';
import { lessonsApi } from '../api/lessons.js';
import { aiApi } from '../api/ai.js';
import { toast } from '../components/toast.js';
import { openModal, confirmModal, confirmDelete } from '../components/modal.js';
import { openLessonEditor } from '../components/lesson-editors.js';
import { escapeHtml, getQueryParam } from '../utils/dom.js';

let me = null;
let courseId = null;
let course = null;
let categories = [];
let modules = [];
let activeStep = 1;
let aiStatus = { available: false, reason: '' };

document.addEventListener('DOMContentLoaded', async () => {
  me = await mountHeader('#header');
  if (!me) return;
  if (me.role === 'admin') { location.replace('/pages/admin.html'); return; }
  if (me.role !== 'teacher') { location.replace('/pages/dashboard.html'); return; }
  mountSidebar('#sidebar', me);
  courseId = parseInt(getQueryParam('id'), 10);
  if (!courseId) { toast.error('Не указан id курса'); return; }

  categories = await categoriesApi.list();
  // Параллельно загружаем статус ИИ — нужен для disable кнопки пакетной генерации
  try { aiStatus = await aiApi.status(); } catch { aiStatus = { available: false, reason: 'Статус ИИ недоступен' }; }
  await loadCourse();

  document.querySelectorAll('.tc-edit-step').forEach(s => {
    s.addEventListener('click', () => switchStep(parseInt(s.dataset.step, 10)));
  });
});

async function loadCourse() {
  course = await coursesApi.get(courseId);
  modules = await coursesApi.modules(courseId);
  document.getElementById('course-title').textContent = course.title;
  renderStep();
}

function switchStep(n) {
  activeStep = n;
  document.querySelectorAll('.tc-edit-step').forEach(s => {
    s.classList.toggle('is-active', parseInt(s.dataset.step, 10) === n);
  });
  renderStep();
}

function renderStep() {
  const root = document.getElementById('step-content');
  if (activeStep === 1) renderBasics(root);
  else if (activeStep === 2) renderStructure(root);
  else if (activeStep === 3) renderContent(root);
  else renderPublish(root);
}

function renderBasics(root) {
  root.innerHTML = `
    <div class="card">
      <div class="form-group">
        <label class="form-label">Название</label>
        <input type="text" class="input" id="title" value="${escapeHtml(course.title)}">
      </div>
      <div class="form-group">
        <label class="form-label">Краткое описание</label>
        <textarea class="textarea" id="short">${escapeHtml(course.short_description || '')}</textarea>
      </div>
      <div class="form-group">
        <label class="form-label">Описание</label>
        <textarea class="textarea" id="desc" style="min-height:160px">${escapeHtml(course.description || '')}</textarea>
      </div>
      <div class="form-row" style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div class="form-group">
          <label class="form-label">Направление</label>
          <select class="select" id="cat">
            ${categories.map(c => `<option value="${c.id}" ${c.id === course.category_id ? 'selected' : ''}>${escapeHtml(c.name)}</option>`).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Уровень</label>
          <select class="select" id="level">
            ${['beginner', 'junior', 'middle', 'senior'].map(l =>
              `<option value="${l}" ${course.level === l ? 'selected' : ''}>${l}</option>`).join('')}
          </select>
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Длительность (минут)</label>
        <input type="number" class="input" id="dur" value="${course.duration_minutes || 0}" min="0">
      </div>
      <button class="btn btn-primary" id="save-basics">Сохранить</button>
      <button class="btn btn-ghost" id="next-step">Далее →</button>
    </div>
  `;
  document.getElementById('save-basics').addEventListener('click', async () => {
    try {
      course = await coursesApi.update(courseId, {
        title: document.getElementById('title').value.trim(),
        short_description: document.getElementById('short').value.trim() || null,
        description: document.getElementById('desc').value.trim() || null,
        category_id: parseInt(document.getElementById('cat').value, 10),
        level: document.getElementById('level').value,
        duration_minutes: parseInt(document.getElementById('dur').value, 10) || 0,
      });
      toast.success('Сохранено');
      document.getElementById('course-title').textContent = course.title;
    } catch (err) { toast.error(err.message || 'Ошибка'); }
  });
  document.getElementById('next-step').addEventListener('click', () => switchStep(2));
}

function renderStructure(root) {
  root.innerHTML = `
    <div class="flex items-center justify-between mb-16">
      <h3>Модули</h3>
      <button class="btn btn-secondary" id="add-module">+ Модуль</button>
    </div>
    <div id="modules-area"></div>
  `;
  const modulesArea = document.getElementById('modules-area');
  if (!modules.length) {
    modulesArea.innerHTML = '<p class="muted">Модулей нет. Добавьте первый.</p>';
  } else {
    modulesArea.innerHTML = modules.map(m => renderModuleHtml(m)).join('');
  }
  if (window.lucide) window.lucide.createIcons();

  document.getElementById('add-module').addEventListener('click', async () => {
    try {
      await coursesApi.createModule(courseId, { title: 'Новый модуль' });
      await loadCourse();
    } catch (err) { toast.error(err.message || 'Ошибка'); }
  });

  modulesArea.querySelectorAll('[data-module-rename]').forEach(inp => {
    inp.addEventListener('blur', async () => {
      try {
        await modulesApi.update(parseInt(inp.dataset.moduleRename, 10), { title: inp.value.trim() });
        toast.success('Сохранено');
      } catch (err) { toast.error(err.message || 'Ошибка'); }
    });
  });

  modulesArea.querySelectorAll('[data-add-lesson]').forEach(btn => {
    btn.addEventListener('click', () => addLessonManual(parseInt(btn.dataset.addLesson, 10)));
  });

  modulesArea.querySelectorAll('[data-add-package]').forEach(btn => {
    btn.addEventListener('click', () => openPackageModal(parseInt(btn.dataset.addPackage, 10)));
  });

  modulesArea.querySelectorAll('[data-delete-module]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const mid = parseInt(btn.dataset.deleteModule, 10);
      const mod = modules.find(m => m.id === mid);
      const name = (mod ? mod.title : 'модуль');
      const ok = await confirmDelete(name);
      if (!ok) return;
      try {
        await modulesApi.remove(mid);
        toast.success('Сохранено');
        await loadCourse();
      } catch (err) { toast.error(err.message || 'Ошибка'); }
    });
  });

  modulesArea.querySelectorAll('[data-delete-lesson]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const lid = parseInt(btn.dataset.deleteLesson, 10);
      const lesson = modules.flatMap(m => m.lessons).find(l => l.id === lid);
      const name = (lesson ? lesson.title : 'урок');
      const ok = await confirmDelete(name);
      if (!ok) return;
      try {
        await lessonsApi.remove(lid);
        toast.success('Сохранено');
        await loadCourse();
      } catch (err) { toast.error(err.message || 'Ошибка'); }
    });
  });

  modulesArea.querySelectorAll('[data-edit-lesson]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const lessonId = parseInt(btn.dataset.editLesson, 10);
      // Находим урок в текущем состоянии modules
      const lesson = modules.flatMap(m => m.lessons).find(l => l.id === lessonId);
      if (!lesson) { toast.error('Урок не найден'); return; }
      // Догружаем полное содержимое (для text-урока — content_markdown)
      let fullLesson = lesson;
      try {
        fullLesson = await lessonsApi.get(lessonId);
      } catch {}
      openLessonEditor(fullLesson, () => loadCourse());
    });
  });
}

function renderModuleHtml(m) {
  return `
    <div class="tc-module">
      <div class="tc-module__head">
        <i data-lucide="folder"></i>
        <input class="tc-module__title-input" data-module-rename="${m.id}" value="${escapeHtml(m.title)}">
        <button class="btn btn-ghost btn-sm" data-delete-module="${m.id}">Удалить</button>
      </div>
      <div class="tc-module__lessons">
        ${m.lessons.map(l => `
          <div class="tc-lesson">
            <i data-lucide="${escapeHtml(l.type === 'quiz' ? 'check-circle' : l.type === 'task' ? 'edit' : 'file-text')}"
               style="width:16px;height:16px"></i>
            <span class="tc-lesson__title">${escapeHtml(l.title)}</span>
            <span class="badge">${escapeHtml(l.type)}</span>
            <button class="btn btn-ghost btn-sm" data-edit-lesson="${l.id}" title="Редактировать">
              <i data-lucide="edit-2" style="width:14px;height:14px"></i>
            </button>
            <button class="btn btn-ghost btn-sm" data-delete-lesson="${l.id}" title="Удалить">×</button>
          </div>
        `).join('')}
      </div>
      <div class="tc-module__add-btns">
        <button class="btn btn-ghost btn-sm" data-add-lesson="${m.id}">+ Урок вручную</button>
        <button class="btn btn-secondary btn-sm"
                data-add-package="${m.id}"
                ${aiStatus.available ? '' : 'disabled'}
                title="${escapeHtml(aiStatus.available ? 'Сгенерировать пакет уроков через ИИ' : aiStatus.reason)}">
          ✨ Создать пакет с ИИ${aiStatus.available ? '' : ' (недоступно)'}
        </button>
      </div>
    </div>
  `;
}

function addLessonManual(moduleId) {
  const body = document.createElement('div');
  body.innerHTML = `
    <div class="form-group">
      <label class="form-label">Название</label>
      <input class="input" id="lesson-title">
    </div>
    <div class="form-group">
      <label class="form-label">Тип урока</label>
      <select class="select" id="lesson-type">
        <option value="text">Текстовый</option>
        <option value="quiz">Тест</option>
        <option value="task">Задание</option>
      </select>
    </div>
  `;
  const footer = document.createElement('div');
  const cancel = document.createElement('button'); cancel.className = 'btn btn-ghost'; cancel.textContent = 'Отмена';
  const save = document.createElement('button'); save.className = 'btn btn-primary'; save.textContent = 'Создать';
  footer.append(cancel, save);

  const m = openModal({ title: 'Новый урок', body, footer });
  cancel.addEventListener('click', m.close);
  save.addEventListener('click', async () => {
    const title = body.querySelector('#lesson-title').value.trim();
    const type = body.querySelector('#lesson-type').value;
    if (!title) return toast.error('Введите название');
    try {
      const { modulesApi } = await import('../api/courses.js');
      await modulesApi.createLesson(moduleId, { title, type });
      toast.success('Сохранено');
      m.close();
      await loadCourse();
    } catch (err) { toast.error(err.message || 'Ошибка'); }
  });
}

// === ИИ-модалка пакетной генерации ===
function openPackageModal(moduleId) {
  const body = document.createElement('div');
  body.innerHTML = `
    <div class="plate mb-16">
      <i data-lucide="info"></i>
      <span>ИИ создаст за один запрос: текст урока, тест из 5 вопросов с правильными ответами и практическое задание с критериями. Лимит 10 пакетов в сутки.</span>
    </div>
    <div class="form-group">
      <label class="form-label">Тема</label>
      <input class="input" id="pkg-topic" maxlength="200" placeholder="например, Goroutines в Go">
    </div>
    <div class="form-group">
      <label class="form-label">Уровень</label>
      <div class="level-group" id="pkg-level">
        ${['beginner', 'junior', 'middle', 'senior'].map(l =>
          `<button type="button" class="level-btn ${course.level === l ? 'is-active' : ''}" data-value="${l}">${l}</button>`).join('')}
      </div>
    </div>
    <div class="form-group">
      <label class="form-label">Длительность чтения</label>
      <div class="level-group" id="pkg-dur">
        <button type="button" class="level-btn" data-value="5">5 мин</button>
        <button type="button" class="level-btn is-active" data-value="10">10 мин</button>
        <button type="button" class="level-btn" data-value="15">15 мин</button>
      </div>
    </div>
    <div class="form-group">
      <label class="form-label">Тип задания</label>
      <div class="level-group" id="pkg-tasktype">
        <button type="button" class="level-btn is-active" data-value="code">code</button>
        <button type="button" class="level-btn" data-value="theory">theory</button>
        <button type="button" class="level-btn" data-value="mixed">mixed</button>
      </div>
    </div>
    <div class="form-group" id="pkg-lang-wrap">
      <label class="form-label">Язык программирования</label>
      <input class="input" id="pkg-lang" value="python">
    </div>
  `;
  const footer = document.createElement('div');
  const cancel = document.createElement('button'); cancel.className = 'btn btn-ghost'; cancel.textContent = 'Отмена';
  const submit = document.createElement('button'); submit.className = 'btn btn-primary'; submit.textContent = '✨ Сгенерировать';
  footer.append(cancel, submit);

  const m = openModal({ title: 'Создание учебного пакета с ИИ', body, footer, size: 'lg', closeOnOverlay: false });
  if (window.lucide) window.lucide.createIcons();

  const state = { level: course.level, duration: 10, task_type: 'code' };
  setupLevelGroup(body.querySelector('#pkg-level'), v => state.level = v);
  setupLevelGroup(body.querySelector('#pkg-dur'), v => state.duration = parseInt(v, 10));
  setupLevelGroup(body.querySelector('#pkg-tasktype'), v => {
    state.task_type = v;
    body.querySelector('#pkg-lang-wrap').classList.toggle('hidden', v !== 'code');
  });

  cancel.addEventListener('click', m.close);
  submit.addEventListener('click', async () => {
    const topic = body.querySelector('#pkg-topic').value.trim();
    if (topic.length < 3) { toast.error('Тема слишком короткая'); return; }
    const lang = body.querySelector('#pkg-lang').value.trim() || 'python';

    showAiLoader(m.body);
    submit.disabled = true;

    try {
      const result = await aiApi.generatePackage({
        module_id: moduleId,
        topic,
        level: state.level,
        duration_minutes: state.duration,
        task_type: state.task_type,
        language: lang,
      });
      m.close();
      toast.success('Пакет создан: 3 урока');
      await loadCourse();
    } catch (err) {
      submit.disabled = false;
      const msg = err.code === 'AI_PROVIDER_NOT_CONFIGURED'
        ? 'ИИ-провайдер не настроен. Обратитесь к админу.'
        : err.code === 'AI_RATE_LIMIT'
          ? 'Лимит ИИ-генерации исчерпан на сегодня'
          : (err.message || 'Ошибка ИИ-генерации');
      toast.error(msg);
      // Восстановить форму
      m.body.innerHTML = '';
      m.body.appendChild(body);
    }
  });
}

function setupLevelGroup(root, onChange) {
  root.addEventListener('click', (e) => {
    const btn = e.target.closest('.level-btn');
    if (!btn) return;
    root.querySelectorAll('.level-btn').forEach(b => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    onChange(btn.dataset.value);
  });
}

let runFrameToggle = false;
let runInterval = null;
function showAiLoader(container) {
  container.innerHTML = `
    <div class="ai-loader">
      <h3>Генерируем урок…</h3>
      <p class="muted">Это может занять до 60 секунд</p>
      <div class="ai-loader__road">
        <img class="ai-loader__dino" id="ai-run-dino" src="/assets/img/dino/dinoRunFirst.png" alt="">
        <img class="ai-loader__cactus" src="/assets/img/dino/kaktusRoad.png" alt="">
      </div>
    </div>
  `;
  if (runInterval) clearInterval(runInterval);
  runInterval = setInterval(() => {
    runFrameToggle = !runFrameToggle;
    const img = document.getElementById('ai-run-dino');
    if (img) img.src = runFrameToggle ? '/assets/img/dino/dinoRunSecond.png' : '/assets/img/dino/dinoRunFirst.png';
  }, 100);
}

function renderContent(root) {
  root.innerHTML = `
    <div class="card">
      <h3 class="mb-16">Контент курса</h3>
      <p class="muted mb-16">Просмотрите все уроки и при необходимости отредактируйте через шаг «Структура».</p>
      ${modules.length === 0 ? '<p>Модулей нет</p>' : modules.map(m => `
        <div class="tc-module">
          <div class="tc-module__head">${escapeHtml(m.title)}</div>
          <div class="tc-module__lessons">
            ${m.lessons.map(l => `
              <div class="tc-lesson">
                <span class="badge">${escapeHtml(l.type)}</span>
                <span class="tc-lesson__title">${escapeHtml(l.title)}</span>
              </div>
            `).join('')}
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderPublish(root) {
  const totalLessons = modules.reduce((s, m) => s + m.lessons.length, 0);
  const ready = modules.length > 0 && totalLessons > 0;
  root.innerHTML = `
    <div class="card">
      <h3 class="mb-16">Публикация</h3>
      <ul class="mb-16">
        <li>Модулей: ${modules.length} ${modules.length > 0 ? '✓' : '✗'}</li>
        <li>Уроков всего: ${totalLessons} ${totalLessons > 0 ? '✓' : '✗'}</li>
        <li>Текущий статус: <strong>${escapeHtml(course.status)}</strong></li>
      </ul>
      ${course.status === 'published'
        ? '<div class="badge badge--success">Курс опубликован</div>'
        : ready
          ? `<button class="btn btn-primary" id="publish-btn">Опубликовать курс</button>`
          : '<p class="muted">Для публикации добавьте минимум 1 модуль и 1 урок</p>'}
    </div>
  `;
  document.getElementById('publish-btn')?.addEventListener('click', async () => {
    try {
      course = await coursesApi.publish(courseId);
      toast.success('Курс опубликован!');
      renderPublish(root);
    } catch (err) { toast.error(err.message || 'Ошибка'); }
  });
}
