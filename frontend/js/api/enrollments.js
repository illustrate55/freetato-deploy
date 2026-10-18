import { api } from './client.js';

export const enrollmentsApi = {
  list: (status) => api.get('/enrollments', status ? { status } : null),
  create: (course_id) => api.post('/enrollments', { course_id }),
  remove: (id) => api.delete(`/enrollments/${id}`),
  progress: (id) => api.get(`/enrollments/${id}/progress`),
};
