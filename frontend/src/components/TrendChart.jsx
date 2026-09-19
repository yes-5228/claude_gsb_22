import { Link } from 'react-router-dom';

import { formatShortDate } from '../utils/format.js';

export default function TrendChart({ points, linkFor }) {
  if (!points?.length) return <div className="empty-block">暂无趋势数据</div>;

  const maxInspections = Math.max(...points.map((point) => point.inspections), 1);
  const maxIssues = Math.max(...points.map((point) => point.issues), 1);
  const scale = Math.max(maxInspections, maxIssues);

  return (
    <>
      <div className="trend-chart">
        {points.map((point) => {
          const body = (
            <>
              <div className="trend-bars">
                <div
                  className="trend-bar"
                  style={{ height: `${(point.inspections / scale) * 100}%` }}
                />
                <div
                  className="trend-bar issues"
                  style={{ height: `${(point.issues / scale) * 100}%` }}
                />
              </div>
              <span className="trend-label">{formatShortDate(point.date)}</span>
            </>
          );
          const title = `${point.date} 巡查 ${point.inspections} 次，问题 ${point.issues} 条，均分 ${point.avg_score ?? '无数据'}`;
          // 当天有巡查或问题时，点击柱子直接进当天明细（口径沿用看板区间）
          const to = linkFor && (point.inspections > 0 || point.issues > 0) ? linkFor(point) : null;
          return to ? (
            <Link className="trend-col is-link" to={to} key={point.date} title={`${title}（点击查看明细）`}>
              {body}
            </Link>
          ) : (
            <div className="trend-col" key={point.date} title={title}>
              {body}
            </div>
          );
        })}
      </div>
      <div className="legend">
        <span>巡查次数</span>
        <span className="issues">新增问题</span>
      </div>
    </>
  );
}
