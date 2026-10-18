import { api } from './client.js';

export const usersApi = {
  me: () => api.get('/users/me'),
  updateMe: (data) => api.patch('/users/me', data),
  myStats: () => api.get('/users/me/stats'),
  list: (query) => api.get('/users', query),
  create: (data) => api.post('/users', data),
  update: (id, data) => api.patch(`/users/${id}`, data),
  remove: (id) => api.delete(`/users/${id}`),
  changeRole: (id, role) => api.post(`/users/${id}/role`, { role }),
};

export const categoriesApi = {
  list: () => api.get('/categories'),
  create: (data) => api.post('/categories', data),
  update: (id, data) => api.patch(`/categories/${id}`, data),
  remove: (id) => api.delete(`/categories/${id}`),
};
