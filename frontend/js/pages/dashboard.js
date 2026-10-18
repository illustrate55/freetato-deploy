import { mountHeader } from '../components/header.js';
import { mountSidebar } from '../components/sidebar.js';
import { mountEmpty } from '../components/empty-state.js';
import { usersApi } from '../api/users.js';
import { enrollmentsApi } from '../api/enrollments.js';
import { escapeHtml } from '../utils/dom.js';
import { pluralize } from '../utils/format.js';

document.addEventListener('DOMContentLoaded', async () => {
  const user = await mountHeader('#header');
  if (!user) return;
  // У админа нет «Главной» — сразу в админ-панель
  if (user.role === 'admin') { location.replace('/pages/admin.html'); return; }
  mountSidebar('#sidebar', user);

  document.getElementById('greeting').textContent = `Здравствуйте, ${user.first_name}!`;

  // Для teacher/admin дашборд студента нерелевантен — убираем студенческие
  // KPI и заголовок, показываем плашку-CTA в их рабочий раздел.
  if (user.role !== 'student') {
    document.querySelector('.dashboard__kpi')?.remove();
    document.getElementById('active-heading')?.remove();
    const root = document.getElementById('active-courses');
    const isAdmin = user.role === 'admin';
    mountEmpty(root, {
      title: isAdmin ? 'Добро пожаловать в админ-панель' : 'Добро пожаловать в раздел преподавания',
      description: isAdmin
        ? 'Управляйте пользователями, курсами и смотрите статистику'
        : 'Создавайте курсы, модули и уроки. Используйте ИИ для генерации пакетов уроков',
      actionText: isAdmin ? 'Открыть админ-панель' : 'Открыть преподавание',
      actionHref: isAdmin ? '/pages/admin.html' : '/pages/teacher.html',
    });
    return;
  }

  try {
    const [stats, enrollments] = await Promise.all([
      usersApi.myStats(),
      enrollmentsApi.list('active'),
    ]);
    document.getElementById('kpi-active').textContent = stats.active_courses;
    document.getElementById('kpi-completed').textContent = stats.completed_courses;

    const root = document.getElementById('active-courses');
    if (!enrollments.items.length) {
      mountEmpty(root, {
        title: 'Вы ещё не записались на курс',
        description: 'Откройте каталог и выберите курс по своему профилю',
        actionText: 'Открыть каталог',
        actionHref: '/pages/catalog.html',
      });
      return;
    }
    root.innerHTML = enrollments.items.map(e => `
      <div class="course-card">
        <div>
          <div class="course-card__plate">
            <i data-lucide="book-open" style="color: var(--color-primary)"></i>
            <strong>${escapeHtml(e.course_title || 'Курс')}</strong>
          </div>
          <div class="course-card__title">${escapeHtml(e.course_title || '')}</div>
          <div class="course-card__meta">
            Пройдено ${e.lessons_completed} из ${e.lessons_total}
            ${pluralize(e.lessons_total, ['урока', 'уроков', 'уроков'])}
            (${e.progress_percent}%)
          </div>
        </div>
        <a class="btn btn-primary" href="${continueLessonHref(e)}">Продолжить</a>
      </div>
    `).join('');
    if (window.lucide) window.lucide.createIcons();
  } catch (err) {
    document.getElementById('active-courses').innerHTML =
      `<p class="muted">Не удалось загрузить курсы: ${escapeHtml(err.message || '')}</p>`;
  }
});

function continueLessonHref(enr) {
  if (enr.last_lesson_id) {
    return `/pages/lesson.html?course=${enr.course_id}&lesson=${enr.last_lesson_id}`;
  }
  return `/pages/course.html?id=${enr.course_id}`;
}
