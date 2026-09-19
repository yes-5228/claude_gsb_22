import { http } from './client.js';

export const statsApi = {
  overview: () => http.get('/stats/overview'),
  /**
   * 看板聚合数据。mode: current=本期 / mom=环比 / yoy=同比；
   * 环比、同比均为与本期等长的区间，由后端统一划分。
   */
  dashboard: ({ mode = 'current', days = 14 } = {}) =>
    http.get('/stats/dashboard', { mode, days }),
};
