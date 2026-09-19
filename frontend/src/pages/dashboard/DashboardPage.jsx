import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { statsApi } from '../../api/stats.js';
import BarList from '../../components/BarList.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import StatCard from '../../components/StatCard.jsx';
import TrendChart from '../../components/TrendChart.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import {
  MODE_OPTIONS,
  RANGE_OPTIONS,
  drillToInspections,
  drillToIssues,
  formatRangeLabel,
  loadSavedRange,
  rangeFromSearchParams,
  saveRange,
} from '../../utils/dashboardRange.js';
import {
  CategoryPanel,
  DistrictPanel,
  IssueStatusPanel,
  RankingPanel,
  RecentInspectionsPanel,
  RecentIssuesPanel,
} from './DashboardPanels.jsx';

/** 初始口径：URL 参数优先（明细页返回），其次上次选择（侧边栏返回），最后默认近 14 天本期。 */
function initialRange(searchParams) {
  return rangeFromSearchParams(searchParams) || loadSavedRange() || { mode: 'current', days: 14 };
}

export default function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [rangeInput, setRangeInput] = useState(() => initialRange(searchParams));
  const { data, loading, error } = useAsync(
    () => statsApi.dashboard(rangeInput),
    [rangeInput.mode, rangeInput.days],
  );

  const applyRange = (next) => {
    setRangeInput(next);
    saveRange(next);
    setSearchParams(
      { dashMode: next.mode, dashDays: String(next.days) },
      { replace: false },
    );
  };

  const overview = data?.overview;
  const effectiveRange = data?.range ?? { ...rangeInput, date_from: '', date_to: '' };
  const rangeEmpty = data ? !data.has_inspections && !data.has_issues : false;

  return (
    <>
      <PageHeader
        title="总览看板"
        description="公厕保洁巡查与问题整改的整体运行情况"
        actions={
          <div className="range-controls">
            <div className="field" style={{ minWidth: 120 }}>
              <label>对比口径</label>
              <select
                value={rangeInput.mode}
                onChange={(event) => applyRange({ ...rangeInput, mode: event.target.value })}
              >
                {MODE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field" style={{ minWidth: 110 }}>
              <label>区间长度</label>
              <select
                value={rangeInput.days}
                onChange={(event) =>
                  applyRange({ ...rangeInput, days: Number(event.target.value) })
                }
              >
                {RANGE_OPTIONS.map((days) => (
                  <option key={days} value={days}>
                    近 {days} 天
                  </option>
                ))}
              </select>
            </div>
          </div>
        }
      />
      <div className="content">
        {data?.range ? (
          <div className="range-banner">
            当前统计口径：<strong>{formatRangeLabel(data.range)}</strong>
            <span className="hint">指标卡、趋势、分布与下钻明细均按此区间统计</span>
          </div>
        ) : null}
        {error ? <div className="alert alert-error">{error.message}</div> : null}
        {/* 口径切换期间整屏一起刷新，避免一半新数据一半旧数据 */}
        {loading ? <div className="loading-block">看板数据按新区间加载中…</div> : null}

        {overview && !loading ? (
          <>
            {rangeEmpty ? (
              <div className="alert alert-info">
                {data.range.mode_label}（{data.range.date_from} ~ {data.range.date_to}
                ）没有巡查记录与问题上报，以下流量指标无数据；下方公厕、未闭环等存量指标仍为当前时点数据。
              </div>
            ) : null}

            <div className="stat-grid">
              <StatCard
                label="在册公厕"
                value={overview.restroom_total}
                unit="座"
                foot={`正常开放 ${overview.restroom_open} 座 · 维修 ${overview.restroom_maintenance} 座（当前存量）`}
              />
              <StatCard
                label={`${data.range.mode_label}巡查记录`}
                value={overview.inspection_total}
                unit="条"
                tone="info"
                foot={
                  overview.inspection_total > 0 ? (
                    <Link to={drillToInspections(data.range)}>查看区间巡查明细 →</Link>
                  ) : (
                    '该区间无巡查记录'
                  )
                }
              />
              <StatCard
                label={`${data.range.mode_label}巡查均分`}
                value={overview.avg_score === null ? null : overview.avg_score.toFixed(1)}
                unit="分"
                tone={
                  overview.avg_score === null
                    ? 'primary'
                    : overview.avg_score >= 85
                      ? 'primary'
                      : 'warning'
                }
                foot="按区间内全部巡查百分制均分"
              />
              <StatCard
                label={`${data.range.mode_label}新增问题`}
                value={overview.issue_total}
                unit="条"
                tone={overview.issue_total > 0 ? 'danger' : 'primary'}
                foot={
                  overview.issue_total > 0 ? (
                    <Link to={drillToIssues(data.range)}>查看区间问题明细 →</Link>
                  ) : (
                    '该区间无问题上报'
                  )
                }
              />
              <StatCard
                label="未闭环问题"
                value={overview.issue_open}
                unit="条"
                tone={overview.issue_open > 0 ? 'danger' : 'primary'}
                foot={`超期未整改 ${overview.issue_overdue} 条（当前存量）`}
              />
              <StatCard
                label={`${data.range.mode_label}问题闭环率`}
                value={overview.rectification_rate === null ? null : overview.rectification_rate.toFixed(1)}
                unit="%"
                tone="info"
                foot={
                  overview.issue_total === 0
                    ? '该区间无问题，暂无闭环率'
                    : `区间上报 ${overview.issue_total} 条 · 已闭环 ${overview.issue_closed} 条`
                }
              />
            </div>

            <div className="grid-2">
              <section className="card">
                <div className="card-title">
                  <h3>巡查与问题趋势</h3>
                  <span className="hint">点击柱子查看当天巡查明细</span>
                </div>
                {data.has_inspections || data.has_issues ? (
                  <TrendChart
                    points={data.inspection_trend}
                    linkFor={(point) =>
                      drillToInspections(
                        { ...effectiveRange, date_from: point.date, date_to: point.date },
                      )
                    }
                  />
                ) : (
                  <div className="empty-block">
                    该区间没有巡查与问题数据，可切换口径或区间长度后重试
                  </div>
                )}
              </section>
              <IssueStatusPanel items={data.issue_by_status} range={data.range} />
            </div>

            <div className="grid-2">
              <CategoryPanel items={data.issue_by_category} range={data.range} />
              <section className="card">
                <div className="card-title">
                  <h3>问题严重程度分布</h3>
                  <span className="hint">点击程度查看区间明细</span>
                </div>
                {data.has_issues ? (
                  <BarList
                    tone="custom"
                    items={data.issue_by_severity.map((item) => ({
                      name: item.name,
                      value: item.value,
                      color: item.name === '紧急' ? '#dc2626' : item.name === '严重' ? '#d97706' : '#64748b',
                      to: drillToIssues(data.range, { severity: item.name }),
                    }))}
                  />
                ) : (
                  <div className="empty-block">该区间暂无问题上报</div>
                )}
              </section>
            </div>

            <div className="grid-2">
              <DistrictPanel items={data.districts} range={data.range} />
              <RankingPanel items={data.top_restrooms} />
            </div>

            <div className="grid-2">
              <RecentIssuesPanel items={data.recent_issues} range={data.range} />
              <RecentInspectionsPanel items={data.recent_inspections} range={data.range} />
            </div>
          </>
        ) : null}
      </div>
    </>
  );
}
