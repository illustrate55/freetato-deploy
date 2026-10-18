import { authApi } from '../api/auth.js';
import { toast } from '../components/toast.js';

// Сессия (access + refresh) живёт только в sessionStorage: при закрытии
// вкладки пользователь возвращается к форме входа. Логины и пароли в
// браузере НЕ сохраняются.
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('login-form');
  const btn = document.getElementById('submit-btn');

  // Подчищаем учётные данные, которые могли сохраниться в браузере раньше.
  ['remembered_logins', 'remembered_flag', 'remembered_email', 'remembered_password', 'refresh_token']
    .forEach((k) => localStorage.removeItem(k));

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = form.email.value.trim();
    const password = form.password.value;

    btn.disabled = true;
    btn.textContent = 'Вход…';
    try {
      const res = await authApi.login(email, password);
      sessionStorage.setItem('access_token', res.access_token);
      sessionStorage.setItem('refresh_token', res.refresh_token);
      // Кэшируем профиль — header/sidebar рендерятся мгновенно без ожидания /me.
      if (res.user) sessionStorage.setItem('user', JSON.stringify(res.user));

      const next = new URLSearchParams(location.search).get('next') || '/pages/dashboard.html';
      location.replace(next);
    } catch (err) {
      const msg = err.code === 'INVALID_CREDENTIALS'
        ? 'Неверный email или пароль'
        : (err.message || 'Ошибка входа');
      toast.error(msg);
      btn.disabled = false;
      btn.textContent = 'Войти';
    }
  });
});
