import { usersApi } from './api/users.js';

/**
 * Если у пользователя нет одной из allowedRoles — отправляет на /dashboard.
 * Возвращает объект пользователя для дальнейшего использования.
 */
export async function roleGuard(allowedRoles) {
  try {
    const me = await usersApi.me();
    if (!allowedRoles.includes(me.role)) {
      location.replace('/pages/dashboard.html');
      return null;
    }
    return me;
  } catch {
    location.replace('/pages/login.html');
    return null;
  }
}
