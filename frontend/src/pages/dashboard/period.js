// 看板统计区间的前端口径：与后端 periods 保持一致，
// 本期/对比区间日期由后端返回，前端只负责展示与拼接明细链接。

export const PERIOD_LENGTHS = [7, 14, 30];

export const COMPARE_OPTIONS = [
  { value: 'mom', label: '环比' },
  { value: 'yoy', label: '同比' },
];

const pad = (num) => String(num).padStart(2, '0');

/** ISO(yyyy-MM-dd) -> MM/DD，用于区间标题。 */
export function formatDay(value) {
  if (!value) return '';
  const [, month, day] = String(value).split('-');
  return `${month}/${day}`;
}

export function formatRange(start, end) {
  return `${formatDay(start)} ~ ${formatDay(end)}`;
}

/** 年/月/日 -> yyyy-MM-dd（后端列表接口 date_from/date_to 要求的格式）。 */
export function toISODate(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/**
 * 拼问题明细链接：自动带上区间与分类/区域筛选。
 * 返回看板用 back=1 让明细页显示“返回看板”，看板区间仍保留在 URL/历史里。
 */
export function buildIssueLink({ start, end, category, district, back }) {
  const params = new URLSearchParams();
  if (start) params.set('date_from', toISODate(start));
  if (end) params.set('date_to', toISODate(end));
  if (category) params.set('category', category);
  if (district) params.set('district', district);
  if (back) params.set('back', '1');
  const query = params.toString();
  return `/issues${query ? `?${query}` : ''}`;
}

/** 拼巡查明细链接（区域分布里点击跳转）。 */
export function buildInspectionLink({ start, end, district, back }) {
  const params = new URLSearchParams();
  if (start) params.set('date_from', toISODate(start));
  if (end) params.set('date_to', toISODate(end));
  if (district) params.set('district', district);
  if (back) params.set('back', '1');
  const query = params.toString();
  return `/inspections${query ? `?${query}` : ''}`;
}
