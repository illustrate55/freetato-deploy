import { api } from './client.js';

export const adminApi = {
  stats: () => api.get('/admin/stats'),
  registrations: (days = 30) => api.get('/admin/stats/registrations', { days }),
  aiUsage: (days = 30) => api.get('/admin/stats/ai-usage', { days }),
};
