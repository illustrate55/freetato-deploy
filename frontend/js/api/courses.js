import { api } from './client.js';

export const coursesApi = {
  list: (query) => api.get('/courses', query),
  get: (id) => api.get(`/courses/${id}`),
  modules: (id) => api.get(`/courses/${id}/modules`),
  create: (data) => api.post('/courses', data),
  update: (id, data) => api.patch(`/courses/${id}`, data),
  publish: (id) => api.post(`/courses/${id}/publish`),
  archive: (id) => api.post(`/courses/${id}/archive`),
  remove: (id) => api.delete(`/courses/${id}`),
  createModule: (courseId, data) => api.post(`/courses/${courseId}/modules`, data),
};

export const modulesApi = {
  update: (id, data) => api.patch(`/modules/${id}`, data),
  remove: (id) => api.delete(`/modules/${id}`),
  createLesson: (moduleId, data) => api.post(`/modules/${moduleId}/lessons`, data),
};
