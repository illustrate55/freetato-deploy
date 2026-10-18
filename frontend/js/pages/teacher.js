import { mountHeader } from '../components/header.js';
import { mountSidebar } from '../components/sidebar.js';
import { mountEmpty } from '../components/empty-state.js';
import { roleGuard } from '../role-guard.js';
import { coursesApi } from '../api/courses.js';
import { toast } from '../components/toast.js';
import { confirmModal } from '../components/modal.js';
import { escapeHtml } from '../utils/dom.js';
import { formatLevel } from '../utils/format.js';

document.addEventListener('DOMContentLoaded', async () => {
  const me = await mountHeader('#header');
  if (!me) return;
  if (me.role === 'admin') { location.replace('/pages/admin.html'); return; }
  if (me.role !== 'teacher') { location.replace('/pages/dashboard.html'); return; }
  mountSidebar('#sidebar', me);

  document.getElementById('create-course-btn').addEventListener('click', async () => {
    // Создаём пустой draft курс с дефолтами и сразу переходим в редактор
    try {
      const cats = await (await import('../api/users.js')).categoriesApi.list();
      const firstCat = cats[0];
      if (!firstCat) {
        toast.error('Сначала администратор должен создать категории');
        return;
      }
      const created = await coursesApi.create({
        title: 'Новый курс',
        category_id: firstCat.id,
        level: 'junior',
        tags: [],
      });
      location.href = `/pages/teacher-course-edit.html?id=${created.id}`;
    } catch (err) {
      toast.error(err.message || 'Ошибка');
    }
  });

  await loadKpiAndCourses(me);
});

async function loadKpiAndCourses(me) {
  let courses = [];
  try {
    const res = await coursesApi.list({ page_size: 100 });
    courses = me.role === 'admin' ? res.items : res.items.filter(c => c.author_id === me.id);
  } catch (err) {
    document.getElementById('my-courses-area').innerHTML = `<p class="muted">${escapeHtml(err.message || '')}</p>`;
    return;
  }

  const totalEnrolled = courses.reduce((s, c) => s + (c.enrollment_count || 0), 0);
  const published = courses.filter(c => c.status === 'published').length;
  const drafts = courses.filter(c => c.status === 'draft').length;

  document.getElementById('kpi-row').innerHTML = `
    <div class="kpi-card"><div class="kpi-card__label">Опубликовано</div><div class="kpi-card__value">${published}</div></div>
    <div class="kpi-card"><div class="kpi-card__label">Черновики</div><div class="kpi-card__value">${drafts}</div></div>
    <div class="kpi-card"><div class="kpi-card__label">Записанных</div><div class="kpi-card__value">${totalEnrolled}</div></div>
  `;

  const root = document.getElementById('my-courses-area');
  if (!courses.length) {
    mountEmpty(root, {
      title: 'Вы ещё не создали ни одного курса',
      description: 'Нажмите «+ Создать курс», чтобы начать',
    });
    return;
  }

  root.innerHTML = `
    <table class="table">
      <thead>
        <tr>
          <th>Название</th><th>Уровень</th><th>Статус</th><th>Записано</th><th></th>
        </tr>
      </thead>
      <tbody>
        ${courses.map(c => `
          <tr>
            <td><a class="link" href="/pages/teacher-course-edit.html?id=${c.id}">${escapeHtml(c.title)}</a></td>
            <td>${escapeHtml(formatLevel(c.level))}</td>
            <td>${renderStatus(c.status)}</td>
            <td>${c.enrollment_count}</td>
            <td>
              <a class="btn btn-ghost btn-sm" href="/pages/course.html?id=${c.id}">Открыть</a>
              <button class="btn btn-ghost btn-sm" data-archive="${c.id}">${c.status === 'archived' ? '' : 'Архив'}</button>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;

  root.querySelectorAll('[data-archive]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const ok = await confirmModal('Архивировать курс?');
      if (!ok) return;
      try {
        await coursesApi.archive(parseInt(btn.dataset.archive, 10));
        toast.success('Курс архивирован');
        await loadKpiAndCourses(me);
      } catch (err) { toast.error(err.message || 'Ошибка'); }
    });
  });
}

function renderStatus(s) {
  if (s === 'published') return '<span class="badge badge--success">Опубликован</span>';
  if (s === 'draft') return '<span class="badge">Черновик</span>';
  return '<span class="badge badge--warning">Архив</span>';
}
