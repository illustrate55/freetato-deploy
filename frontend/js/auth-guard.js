// Сразу после <head>: если в этой вкладке нет токенов — на страницу входа.
// (localStorage не проверяем: persist-сессии больше нет — закрытие браузера
// гарантированно отправит на форму логина.)
(function () {
  const access = sessionStorage.getItem('access_token');
  const refresh = sessionStorage.getItem('refresh_token');
  if (!access && !refresh) {
    const next = encodeURIComponent(location.pathname + location.search);
    location.replace('/pages/login.html?next=' + next);
  }
})();
