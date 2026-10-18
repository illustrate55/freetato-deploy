// Форматирование дат, чисел, инициалов.

export function initials(firstName = '', lastName = '') {
  const a = (firstName || '').trim()[0] || '';
  const b = (lastName || '').trim()[0] || '';
  return (a + b).toUpperCase() || '?';
}

export function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

export function formatDateTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function pluralize(n, forms) {
  // forms: ['курс', 'курса', 'курсов']
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return forms[0];
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return forms[1];
  return forms[2];
}

export function formatLevel(level) {
  return {
    beginner: 'Начинающий',
    junior: 'Junior',
    middle: 'Middle',
    senior: 'Senior',
  }[level] || level;
}

export function formatLessonType(type) {
  return { text: 'Текст', quiz: 'Тест', task: 'Задание' }[type] || type;
}

export function lessonTypeIcon(type) {
  return { text: 'file-text', quiz: 'check-circle', task: 'edit' }[type] || 'circle';
}
