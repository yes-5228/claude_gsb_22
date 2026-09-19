/**
 * 看板统计口径（本期 / 环比 / 同比）在看板与明细页之间的传递。
 * 区间由后端统一划分，明细页只消费看板返回的日期，保证三处合计同口径。
 */

export const RANGE_OPTIONS = [7, 14, 30];
export const MODE_OPTIONS = [
  { value: 'current', label: '本期' },
  { value: 'mom', label: '环比区间' },
  { value: 'yoy', label: '同比区间' },
];

const STORAGE_KEY = 'dashboard.range';
const VALID_MODES = new Set(MODE_OPTIONS.map((item) => item.value));

export function isValidMode(mode) {
  return VALID_MODES.has(mode);
}

export function clampDays(days) {
  const value = Number(days);
  return RANGE_OPTIONS.includes(value) ? value : 14;
}

/** 从 URL 查询参数解析口径（看板、明细页共用）。 */
export function rangeFromSearchParams(searchParams) {
  const mode = searchParams.get('dashMode');
  const days = Number(searchParams.get('dashDays'));
  if (!isValidMode(mode) || !RANGE_OPTIONS.includes(days)) return null;
  return { mode, days };
}

/** 读取上次看板使用的口径（从明细页点侧边栏回看板时恢复用）。 */
export function loadSavedRange() {
  try {
    const raw = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null');
    if (raw && isValidMode(raw.mode) && RANGE_OPTIONS.includes(Number(raw.days))) {
      return { mode: raw.mode, days: Number(raw.days) };
    }
  } catch {
    // 忽略损坏的缓存
  }
  return null;
}

export function saveRange(range) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(range));
  } catch {
    // 无痕模式等场景下 sessionStorage 不可用时静默降级
  }
}

export function modeLabel(mode) {
  return MODE_OPTIONS.find((item) => item.value === mode)?.label || '本期';
}

export function formatRangeLabel(range) {
  return `${modeLabel(range.mode)}（${range.date_from} ~ ${range.date_to}，共 ${range.days} 天）`;
}

/**
 * 生成看板 → 明细列表的下钻链接，自动带上：
 * 看板口径（dashMode/dashDays，用于返回看板恢复）+ 区间日期 + 额外筛选（分类/区域等）。
 */
export function drillToIssues(range, extra = {}) {
  const params = new URLSearchParams({
    dashMode: range.mode,
    dashDays: String(range.days),
    date_from: range.date_from,
    date_to: range.date_to,
  });
  Object.entries(extra).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') params.set(key, value);
  });
  return `/issues?${params.toString()}`;
}

export function drillToInspections(range, extra = {}) {
  const params = new URLSearchParams({
    dashMode: range.mode,
    dashDays: String(range.days),
    date_from: range.date_from,
    date_to: range.date_to,
  });
  Object.entries(extra).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') params.set(key, value);
  });
  return `/inspections?${params.toString()}`;
}

/** 从明细页返回看板时恢复原口径。 */
export function backToDashboardLink(range) {
  return range ? `/?dashMode=${range.mode}&dashDays=${range.days}` : '/';
}
