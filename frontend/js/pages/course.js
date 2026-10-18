import { mountHeader } from '../components/header.js';
import { mountSidebar } from '../components/sidebar.js';
import { coursesApi } from '../api/courses.js';
import { enrollmentsApi } from '../api/enrollments.js';
import { toast } from '../components/toast.js';
import { escapeHtml, getQueryParam } from '../utils/dom.js';
import { formatLevel, lessonTypeIcon, formatLessonType, pluralize } from '../utils/format.js';

let me = null;
let course = null;
let modules = [];
let myEnrollment = null;
let progressData = null;

document.addEventListener('DOMContentLoaded', async () => {
  me = await mountHeader('#header');
  if (!me) return;
  mountSidebar('#sidebar', me);

  const id = parseInt(getQueryParam('id'), 10);
  if (!id) return renderError('Не указан id курса');

  await loadCourse(id);
});

async function loadCourse(id) {
  try {
    course = await coursesApi.get(id);
  } catch (err) {
    if (err.code === 'COURSE_NOT_IN_PROFILE') {
      return renderNotInProfile();
    }
    return renderError(err.message || 'Не удалось загрузить курс');
  }

  modules = await coursesApi.modules(id);

  if (me.role === 'student') {
    const list = await enrollmentsApi.list();
    myEnrollment = list.items.find(e => e.course_id === id) || null;
    if (myEnrollment) {
      try { progressData = await enrollmentsApi.progress(myEnrollment.id); } catch {}
    }
  }
  render();
}

function renderError(msg) {
  document.getElementById('content').innerHTML = `<div class="card"><p class="muted">${escapeHtml(msg)}</p></div>`;
}

function renderNotInProfile() {
  document.getElementById('content').innerHTML = `
    <div class="plate plate--warning mb-16">
      <i data-lucide="alert-triangle"></i>
      <span>Этот курс не входит в вашу программу.
        <a href="/pages/profile.html?tab=preferences" class="link">Изменить профиль обучения →</a>
      </span>
    </div>
  `;
  if (window.lucide) window.lucide.createIcons();
}

function render() {
  const enrolled = !!myEnrollment;
  const progress = enrolled ? myEnrollment.progress_percent : 0;
  const completed = myEnrollment && myEnrollment.status === 'completed';
  const totalLessons = myEnrollment?.lessons_total || modules.reduce((s, m) => s + m.lessons.length, 0);

  let actionHtml;
  if (me.role === 'student') {
    if (completed) {
      actionHtml = `<div class="badge badge--success" style="height:36px;font-size:14px">✓ Курс пройден</div>`;
    } else if (!enrolled) {
      actionHtml = `<button class="btn btn-primary btn-lg" id="enroll-btn">Записаться</button>`;
    } else if (progress === 0) {
      actionHtml = `<a class="btn btn-primary btn-lg" href="${firstLessonHref()}">Начать обучение</a>`;
    } else {
      actionHtml = `<a class="btn btn-primary btn-lg" href="${continueHref()}">Продолжить</a>`;
    }
  } else {
    actionHtml = `<a class="btn btn-secondary" href="/pages/teacher-course-edit.html?id=${course.id}">Редактировать</a>`;
  }

  document.getElementById('content').innerHTML = `
    <div class="course-hero">
      <div class="course-hero__breadcrumb">
        <a href="/pages/catalog.html">Каталог</a> / ${escapeHtml(course.title)}
      </div>
      <h1 class="course-hero__title">${escapeHtml(course.title)}</h1>
      <p class="course-hero__desc">${escapeHtml(course.short_description || course.description || '')}</p>
      <div class="course-hero__meta">
        <span>📚 ${escapeHtml(formatLevel(course.level))}</span>
        <span>⏱ ${course.duration_minutes || '—'} мин</span>
        <span>👥 ${course.enrollment_count} записанных</span>
      </div>
      ${enrolled && !completed ? `
        <div class="course-hero__progress">
          <div class="course-hero__progress-label">
            Пройдено ${myEnrollment.lessons_completed} из ${totalLessons}
            ${pluralize(totalLessons, ['урока', 'уроков', 'уроков'])}, ${progress}%
          </div>
          <div class="progress progress--lg">
            <div class="progress__fill" style="width: ${progress}%"></div>
          </div>
        </div>
      ` : ''}
      <div class="course-hero__action">${actionHtml}</div>
    </div>

    <div class="course-body">
      <div class="course-body__main">
        <h2 class="mb-16">Программа курса</h2>
        ${modules.length ? modules.map(m => renderModule(m)).join('') : '<p class="muted">Модулей пока нет</p>'}
      </div>
      <div class="course-body__side">
        <h3 class="mb-16">Описание</h3>
        <div>${escapeHtml(course.description || course.short_description || 'Описание не указано')}</div>
      </div>
    </div>
  `;
  if (window.lucide) window.lucide.createIcons();

  document.getElementById('enroll-btn')?.addEventListener('click', enroll);
}

function renderModule(m) {
  return `
    <div class="module">
      <div class="module__header">
        <i data-lucide="folder"></i>
        ${escapeHtml(m.title)}
      </div>
      <div class="module__lessons">
        ${m.lessons.map(l => renderLessonRow(l)).join('')}
      </div>
    </div>
  `;
}

function renderLessonRow(l) {
  const status = progressData?.lessons_status?.[String(l.id)];
  const isDone = status === 'completed';
  const enrolled = !!myEnrollment;
  const href = enrolled
    ? `/pages/lesson.html?course=${course.id}&lesson=${l.id}`
    : 'javascript:void(0)';
  return `
    <div class="lesson-row">
      <span class="lesson-row__icon"><i data-lucide="${lessonTypeIcon(l.type)}" style="width:16px;height:16px"></i></span>
      <a href="${href}">${escapeHtml(l.title)}</a>
      <span class="badge">${escapeHtml(formatLessonType(l.type))}</span>
      <span class="lesson-row__status ${isDone ? 'is-done' : ''}">${isDone ? '✓' : '○'}</span>
    </div>
  `;
}

function firstLessonHref() {
  const firstLesson = modules.flatMap(m => m.lessons)[0];
  if (!firstLesson) return `/pages/course.html?id=${course.id}`;
  return `/pages/lesson.html?course=${course.id}&lesson=${firstLesson.id}`;
}

function continueHref() {
  if (myEnrollment.last_lesson_id) {
    return `/pages/lesson.html?course=${course.id}&lesson=${myEnrollment.last_lesson_id}`;
  }
  return firstLessonHref();
}

async function enroll() {
  try {
    myEnrollment = await enrollmentsApi.create(course.id);
    toast.success('Вы записаны на курс');
    try { progressData = await enrollmentsApi.progress(myEnrollment.id); } catch {}
    course.enrollment_count = (course.enrollment_count || 0) + 1;
    render();
  } catch (err) {
    if (err.code === 'COURSE_NOT_IN_PROFILE') return renderNotInProfile();
    toast.error(err.message || 'Не удалось записаться');
  }
}
