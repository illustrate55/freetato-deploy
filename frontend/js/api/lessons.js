import { api } from './client.js';

export const lessonsApi = {
  get: (id) => api.get(`/lessons/${id}`),
  update: (id, data) => api.patch(`/lessons/${id}`, data),
  remove: (id) => api.delete(`/lessons/${id}`),
  complete: (id) => api.post(`/lessons/${id}/complete`),
};
