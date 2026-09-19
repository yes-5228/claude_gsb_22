import { http } from './client.js';

export const statsApi = {
  overview: () => http.get('/stats/overview'),
  dashboard: ({ days = 14, compare = 'mom' } = {}) =>
    http.get('/stats/dashboard', { trend_days: days, compare }),
};
