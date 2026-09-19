import { useSearchParams } from 'react-router-dom';

import { statsApi } from '../../api/stats.js';
import BarList from '../../components/BarList.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import StatCard from '../../components/StatCard.jsx';
import TrendChart from '../../components/TrendChart.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import {
  CategoryPanel,
  DistrictPanel,
  IssueStatusPanel,
  RankingPanel,
  RecentInspectionsPanel,
  RecentIssuesPanel,
} from './DashboardPanels.jsx';
import { COMPARE_OPTIONS, PERIOD_LENGTHS, formatRange } from './period.js';

function clampDays(value) {
  const days = Number(value);
  return PERIOD_LENGTHS.includes(days) ? days : 14;
}

/** 对比口径脚注：区分“对比区间无数据”与真实的 0，绝不把无数据说成 0。 */
function compareFoot({ hasData, mode, current, previous, kind }) {
  const label = mode === 'yoy' ? '同比去年同期' : '环比上期';
  if (previous == null || !hasData) {
    return { text: `${label}区间无数据`, muted: true };
  }
  if (kind === 'score' || kind === 'rate') {
    const unit = kind === 'score' ? ' 分' : '%';
    // 本期该指标无数据（如整段没有巡查）时只展示对比期数值，不做差值
    if (current == null) {
      return { text: `${label} ${previous.toFixed(1)}${unit}，本期无数据`, muted: true };
    }
    const diff = current - previous;
    const suffix = kind === 'score' ? ' 分' : ' 个百分点';
    return {
      text: `${label} ${previous.toFixed(1)}${unit}（${diff > 0 ? '+' : ''}${diff.toFixed(1)}${suffix}）`,
      up: diff > 0,
      down: diff < 0,
    };
  }
  const diff = current - previous;
  let change;
  if (previous === 0) {
    change = diff === 0 ? '持平' : '上期为 0';
  } else {
    change = `${diff > 0 ? '+' : ''}${((diff / previous) * 100).toFixed(0)}%`;
  }
  return {
    text: `${label} ${previous} 条（${change}）`,
    up: diff > 0,
    down: diff < 0,
  };
}

function Foot({ foot }) {
  if (!foot) return null;
  const cls = foot.muted ? 'foot-muted' : foot.up ? 'foot-up' : foot.down ? 'foot-down' : '';
  return <div className={`foot ${cls}`}>{foot.text}</div>;
}

export default function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const days = clampDays(searchParams.get('days'));
  const compare = searchParams.get('compare') === 'yoy' ? 'yoy' : 'mom';

  // 看板所有面板来自同一次请求返回的同一个 data 对象：
  // 切换口径时整屏一起替换，从机制上杜绝一半新一半旧。
  const { data, loading, error } = useAsync(
    () => statsApi.dashboard({ days, compare }),
    [days, compare],
  );

  const patchParams = (patch) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        Object.entries(patch).forEach(([key, value]) => next.set(key, String(value)));
        return next;
      },
      { replace: true },
    );
  };

  const overview = data?.overview;
  const period = data?.period;
  const compareData = data?.compare;
  const trendInspections = (data?.inspection_trend || []).reduce((s, p) => s + p.inspections, 0);
  const trendIssues = (data?.inspection_trend || []).reduce((s, p) => s + p.issues, 0);

  const controls = (
    <div className="dashboard-controls">
      <div className="segmented" role="group" aria-label="对比口径">
        {COMPARE_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={compare === option.value ? 'active' : ''}
            aria-pressed={compare === option.value}
            onClick={() => patchParams({ compare: option.value })}
          >
            {option.label}
          </button>
        ))}
      </div>
      <div className="field" style={{ minWidth: 120 }}>
        <label>区间长度</label>
        <select value={days} onChange={(event) => patchParams({ days: Number(event.target.value) })}>
          {PERIOD_LENGTHS.map((length) => (
            <option key={length} value={length}>
              近 {length} 天
            </option>
          ))}
        </select>
      </div>
    </div>
  );

  return (
    <>
      <PageHeader
        title="总览看板"
        description="公厕保洁巡查与问题整改的整体运行情况，支持环比 / 同比同口径对比"
        actions={controls}
      />
      <div className="content">
        {error ? <div className="alert alert-error">{error.message}</div> : null}
        {loading && !data ? <div className="loading-block">看板数据加载中…</div> : null}

        {data && overview && period ? (
          <div className="refresh-mask-wrap">
            {loading ? (
              <div className="refresh-mask">口径切换中，整屏数据将一起刷新…</div>
            ) : null}

            <div className="period-bar">
              <span className="period-main">
                统计区间 <strong>{formatRange(period.start, period.end)}</strong>（近 {period.days}{' '}
                天）
              </span>
              <span className="period-compare">
                {compare === 'yoy' ? '同比' : '环比'}对比区间{' '}
                {formatRange(period.compare_start, period.compare_end)}
              </span>
            </div>

            {!data.has_data ? (
              <div className="alert alert-info">
                {formatRange(period.start, period.end)} 区间内没有任何巡查或问题数据：下方数量为真实的
                0，但巡查均分、闭环率因无数据显示“—”而非 0，各分布图也提示“区间内暂无数据”。在册公厕、未闭环、超期等存量指标不受区间影响，仍为当前真实值。可切换区间长度或
                {compare === 'yoy' ? '改为环比' : '改为同比'}查看其它区间。
              </div>
            ) : null}

            <div className="stat-grid">
              <StatCard
                label="在册公厕"
                value={overview.restroom_total}
                unit="座"
                foot={`正常开放 ${overview.restroom_open} 座 · 维修 ${overview.restroom_maintenance} 座`}
              />
              <StatCard
                label={`区间巡查总数（近 ${period.days} 天）`}
                value={overview.inspection_total}
                unit="条"
                tone="info"
                foot={<Foot
                  foot={compareFoot({
                    hasData: compareData.has_data,
                    mode: compare,
                    current: overview.inspection_total,
                    previous: compareData.inspection_total,
                  })}
                />}
              />
              <StatCard
                label="区间巡查均分"
                value={overview.avg_score == null ? '—' : overview.avg_score.toFixed(1)}
                unit={overview.avg_score == null ? '' : '分'}
                tone={
                  overview.avg_score == null
                    ? 'primary'
                    : overview.avg_score >= 85
                      ? 'primary'
                      : 'warning'
                }
                foot={<Foot
                  foot={compareFoot({
                    hasData: compareData.has_data,
                    mode: compare,
                    current: overview.avg_score,
                    previous: compareData.avg_score,
                    kind: 'score',
                  })}
                />}
              />
              <StatCard
                label="区间新增问题"
                value={overview.issue_total}
                unit="条"
                tone={overview.issue_total > 0 ? 'danger' : 'primary'}
                foot={<Foot
                  foot={compareFoot({
                    hasData: compareData.has_data,
                    mode: compare,
                    current: overview.issue_total,
                    previous: compareData.issue_total,
                  })}
                />}
              />
              <StatCard
                label="未闭环问题（当前）"
                value={overview.issue_open}
                unit="条"
                tone={overview.issue_open > 0 ? 'danger' : 'primary'}
                foot={`本区间上报且仍未闭环 ${overview.issue_total - overview.issue_closed} 条`}
              />
              <StatCard
                label="超期未整改（当前）"
                value={overview.issue_overdue}
                unit="条"
                tone={overview.issue_overdue > 0 ? 'danger' : 'primary'}
                foot="超过整改期限仍未闭环"
              />
              <StatCard
                label="区间问题闭环率"
                value={overview.rectification_rate == null ? '—' : overview.rectification_rate.toFixed(1)}
                unit={overview.rectification_rate == null ? '' : '%'}
                tone="info"
                foot={<Foot
                  foot={compareFoot({
                    hasData: compareData.has_data,
                    mode: compare,
                    current: overview.rectification_rate,
                    previous: compareData.rectification_rate,
                    kind: 'rate',
                  })}
                />}
              />
            </div>

            <div className="grid-2">
              <section className="card">
                <div className="card-title">
                  <h3>巡查与问题趋势</h3>
                  <span className="hint">
                    {formatRange(period.start, period.end)} · 合计 巡查 {trendInspections} / 问题{' '}
                    {trendIssues}
                  </span>
                </div>
                <TrendChart points={data.inspection_trend} />
              </section>
              <IssueStatusPanel items={data.issue_by_status} period={period} />
            </div>

            <div className="grid-2">
              <CategoryPanel items={data.issue_by_category} period={period} />
              <section className="card">
                <div className="card-title">
                  <h3>问题严重程度分布</h3>
                  <span className="hint">区间合计 {trendIssues} 条</span>
                </div>
                <BarList
                  items={data.issue_by_severity.map((item) => ({
                    name: item.name,
                    value: item.value,
                    color: item.name === '紧急' ? '#dc2626' : item.name === '严重' ? '#d97706' : '#64748b',
                  }))}
                  tone="custom"
                  emptyText={`${formatRange(period.start, period.end)} 区间内暂无问题数据`}
                />
              </section>
            </div>

            <div className="grid-2">
              <DistrictPanel items={data.districts} period={period} />
              <RankingPanel items={data.top_restrooms} period={period} />
            </div>

            <div className="grid-2">
              <RecentIssuesPanel items={data.recent_issues} period={period} />
              <RecentInspectionsPanel items={data.recent_inspections} period={period} />
            </div>
          </div>
        ) : null}
      </div>
    </>
  );
}
