import { api } from './client.js';

export const tasksApi = {
  get: (id) => api.get(`/tasks/${id}`),
  getFull: (id) => api.get(`/tasks/${id}/full`),
  update: (id, data) => api.patch(`/tasks/${id}`, data),
  submit: (id, solution) => api.post(`/tasks/${id}/submissions`, { solution }),
};

export const submissionsApi = {
  get: (id) => api.get(`/submissions/${id}`),
  my: (query) => api.get('/submissions/my', query),
};
