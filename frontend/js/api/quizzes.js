import { api } from './client.js';

export const quizzesApi = {
  get: (id) => api.get(`/quizzes/${id}`),
  getFull: (id) => api.get(`/quizzes/${id}/full`),
  updateFull: (id, data) => api.put(`/quizzes/${id}/full`, data),
  startAttempt: (id) => api.post(`/quizzes/${id}/attempts`),
  addQuestion: (quizId, data) => api.post(`/quizzes/${quizId}/questions`, data),
};

export const attemptsApi = {
  submit: (id, answers) => api.post(`/attempts/${id}/submit`, { answers }),
  result: (id) => api.get(`/attempts/${id}/result`),
};
