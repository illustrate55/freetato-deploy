import { mountHeader } from '../components/header.js';
import { coursesApi } from '../api/courses.js';
import { lessonsApi } from '../api/lessons.js';
import { enrollmentsApi } from '../api/enrollments.js';
import { toast } from '../components/toast.js';
import { escapeHtml, getQueryParam } from '../utils/dom.js';
import { lessonTypeIcon } from '../utils/format.js';

let me = null;
let course = null;
let courseId = null;
let lessonId = null;
let modules = [];
let currentLesson = null;
let myEnrollment = null;
let progressData = null;

document.addEventListener('DOMContentLoaded', async () => {
  me = await mountHeader('#header');
  if (!me) return;
  courseId = parseInt(getQueryParam('course'), 10);
  lessonId = parseInt(getQueryParam('lesson'), 10);
  if (!courseId || !lessonId) {
    document.getElementById('lesson-content').innerHTML = '<p class="muted">Неверные параметры</p>';
    return;
  }

  try {
    [course, modules] = await Promise.all([coursesApi.get(courseId), coursesApi.modules(courseId)]);
    const list = await enrollmentsApi.list();
    myEnrollment = list.items.find(e => e.course_id === courseId) || null;
    if (myEnrollment) {
      try { progressData = await enrollmentsApi.progress(myEnrollment.id); } catch {}
    }
    currentLesson = await lessonsApi.get(lessonId);
  } catch (err) {
    document.getElementById('lesson-content').innerHTML = `<p class="muted">${escapeHtml(err.message || '')}</p>`;
    return;
  }

  renderSidebar();
  renderContent();
});

function renderSidebar() {
  const root = document.getElementById('lesson-sidebar');
  root.innerHTML = `
    <div class="lesson-sidebar__title">${escapeHtml(course.title)}</div>
    ${modules.map(m => `
      <div class="lesson-sidebar__module ${m.lessons.some(l => l.id === lessonId) ? 'is-open' : ''}">
        <div class="lesson-sidebar__module-title">
          <i data-lucide="folder" style="width:14px;height:14px"></i>
          ${escapeHtml(m.title)}
        </div>
        <div class="lesson-sidebar__lessons">
          ${m.lessons.map(l => {
            const isDone = progressData?.lessons_status?.[String(l.id)] === 'completed';
            const isActive = l.id === lessonId;
            return `
              <a class="lesson-sidebar__lesson ${isActive ? 'is-active' : ''}"
                 href="/pages/lesson.html?course=${courseId}&lesson=${l.id}">
                <span class="lesson-sidebar__lesson__status ${isDone ? 'is-done' : ''}">${isDone ? '✓' : '○'}</span>
                <i data-lucide="${lessonTypeIcon(l.type)}" style="width:14px;height:14px"></i>
                <span style="flex:1">${escapeHtml(l.title)}</span>
              </a>
            `;
          }).join('')}
        </div>
      </div>
    `).join('')}
  `;
  root.querySelectorAll('.lesson-sidebar__module-title').forEach(t => {
    t.addEventListener('click', () => t.parentElement.classList.toggle('is-open'));
  });
  if (window.lucide) window.lucide.createIcons();
}

function findAdjacentLessons() {
  const all = modules.flatMap(m => m.lessons);
  const idx = all.findIndex(l => l.id === lessonId);
  return { prev: idx > 0 ? all[idx - 1] : null, next: idx >= 0 && idx < all.length - 1 ? all[idx + 1] : null };
}

function renderContent() {
  const root = document.getElementById('lesson-content');
  const { prev, next } = findAdjacentLessons();

  let bodyHtml = '';
  let primaryActionHtml = '';
  if (currentLesson.type === 'text') {
    const md = currentLesson.content_markdown || '';
    const html = window.marked ? window.marked.parse(md, { sanitize: true }) : escapeHtml(md);
    bodyHtml = `<div class="lesson-content__body">${html}</div>`;
    primaryActionHtml = `<button class="btn btn-primary" id="complete-btn">Завершить урок ✓</button>`;
  } else if (currentLesson.type === 'quiz') {
    bodyHtml = `
      <div class="lesson-content__body">
        <p>Это тест. Перейдите к прохождению, чтобы получить вопросы и ответить на них.</p>
      </div>
    `;
    primaryActionHtml = `
      <a class="btn btn-primary" href="/pages/quiz.html?id=${currentLesson.quiz_id}&course=${courseId}&lesson=${currentLesson.id}">
        Начать тест →
      </a>
    `;
  } else if (currentLesson.type === 'task') {
    bodyHtml = `
      <div class="lesson-content__body">
        <p>Практическое задание. Откройте, чтобы увидеть условие и сдать решение на проверку ИИ.</p>
      </div>
    `;
    primaryActionHtml = `
      <a class="btn btn-primary" href="/pages/task.html?id=${currentLesson.task_id}&course=${courseId}&lesson=${currentLesson.id}">
        Открыть задание →
      </a>
    `;
  }

  root.innerHTML = `
    <div class="lesson-content__breadcrumb">
      <a href="/pages/course.html?id=${courseId}">${escapeHtml(course.title)}</a>
    </div>
    <h1 class="lesson-content__title">${escapeHtml(currentLesson.title)}</h1>
    ${bodyHtml}
    <div class="lesson-content__nav">
      ${prev ? `<a class="btn btn-ghost" href="/pages/lesson.html?course=${courseId}&lesson=${prev.id}">← Предыдущий</a>` : '<span></span>'}
      <div class="lesson-content__nav-actions">
        ${primaryActionHtml}
        ${next ? `<a class="btn btn-ghost" href="/pages/lesson.html?course=${courseId}&lesson=${next.id}">Следующий →</a>` : ''}
      </div>
    </div>
  `;

  document.getElementById('complete-btn')?.addEventListener('click', async () => {
    try {
      await lessonsApi.complete(currentLesson.id);
      toast.success('Урок пройден');
      const { next } = findAdjacentLessons();
      if (next) location.href = `/pages/lesson.html?course=${courseId}&lesson=${next.id}`;
      else location.href = `/pages/course.html?id=${courseId}`;
    } catch (err) {
      toast.error(err.message || 'Ошибка');
    }
  });
}
