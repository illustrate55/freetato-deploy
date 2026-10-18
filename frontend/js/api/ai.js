import { api } from './client.js';

export const aiApi = {
  status: () => api.get('/ai/status'),
  generatePackage: (payload) => api.post('/ai/lessons/generate-package', payload),
};
