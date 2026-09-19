import { Link, useSearchParams } from 'react-router-dom';

import { backToDashboardLink, modeLabel, rangeFromSearchParams } from '../utils/dashboardRange.js';

/**
 * 从看板下钻到明细页时展示的口径提示条：
 * 标明当前筛选来自哪个看板区间，并提供返回看板（恢复原口径）的入口。
 */
export default function DashboardDrillBanner({ dateFrom, dateTo }) {
  const [searchParams] = useSearchParams();
  const range = rangeFromSearchParams(searchParams);
  if (!range || !dateFrom || !dateTo) return null;

  return (
    <div className="alert alert-info drill-banner">
      <span>
        来自看板<strong>{modeLabel(range.mode)}</strong>口径，已按区间
        <strong> {dateFrom} ~ {dateTo} </strong>
        自动筛选，合计与看板一致。
      </span>
      <Link className="btn btn-sm" to={backToDashboardLink(range)}>
        ← 返回看板（保持{modeLabel(range.mode)}口径）
      </Link>
    </div>
  );
}
