// Базовый HTTP-клиент с авто-refresh при 401.
const BASE_URL = window.API_BASE_URL || '/api/v1';

async function refreshAccess() {
  const refresh = sessionStorage.getItem('refresh_token');
  if (!refresh) return null;
  const r = await fetch(BASE_URL + '/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!r.ok) return null;
  const d = await r.json();
  sessionStorage.setItem('access_token', d.access_token);
  sessionStorage.setItem('refresh_token', d.refresh_token);
  return d.access_token;
}

async function request(method, path, { body, query, isForm } = {}) {
  let url = BASE_URL + path;
  if (query) {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) {
      if (v === undefined || v === null || v === '') continue;
      params.set(k, String(v));
    }
    const qs = params.toString();
    if (qs) url += '?' + qs;
  }

  let access = sessionStorage.getItem('access_token');

  // Если access протух за время сессии (15 мин TTL), но refresh ещё жив в
  // sessionStorage — обновляем access заранее, чтобы запрос не упал в 401.
  if (!access && sessionStorage.getItem('refresh_token')) {
    access = await refreshAccess();
  }

  const doFetch = async () => {
    const headers = {};
    if (access) headers['Authorization'] = 'Bearer ' + access;
    if (!isForm && body !== undefined) headers['Content-Type'] = 'application/json';
    return fetch(url, {
      method,
      headers,
      body: body !== undefined ? (isForm ? body : JSON.stringify(body)) : undefined,
    });
  };

  let r = await doFetch();

  if (r.status === 401 && sessionStorage.getItem('refresh_token')) {
    access = await refreshAccess();
    if (access) {
      r = await doFetch();
    } else {
      sessionStorage.clear();
      const next = encodeURIComponent(location.pathname + location.search);
      location.replace('/pages/login.html?next=' + next);
      throw new Error('Session expired');
    }
  }

  if (!r.ok) {
    let err;
    try { err = await r.json(); } catch { err = { error: { message: r.statusText } }; }
    const message = err?.error?.message || err?.message || `HTTP ${r.status}`;
    const code = err?.error?.code;
    const error = new Error(message);
    error.status = r.status;
    error.code = code;
    error.body = err;
    throw error;
  }

  if (r.status === 204) return null;
  const ct = r.headers.get('content-type') || '';
  if (ct.includes('application/json')) return r.json();
  return r.text();
}

export const api = {
  get:    (p, query)    => request('GET', p, { query }),
  post:   (p, body)     => request('POST', p, { body }),
  put:    (p, body)     => request('PUT', p, { body }),
  patch:  (p, body)     => request('PATCH', p, { body }),
  delete: (p)           => request('DELETE', p),
  upload: (p, formData) => request('POST', p, { body: formData, isForm: true }),
};

export function logoutClient() {
  sessionStorage.clear();
}
