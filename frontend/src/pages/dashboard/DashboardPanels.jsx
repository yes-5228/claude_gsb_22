import { Link } from 'react-router-dom';

import BarList from '../../components/BarList.jsx';
import DataTable from '../../components/DataTable.jsx';
import { ScorePill, SeverityTag, StatusTag } from '../../components/Tags.jsx';
import { formatDateTime } from '../../utils/format.js';
import {
  buildInspectionLink,
  buildIssueLink,
  formatRange,
} from './period.js';

const STATUS_COLORS = {
  待整改: '#dc2626',
  整改中: '#d97706',
  待验收: '#2563eb',
  已完成: '#15803d',
  已关闭: '#94a3b8',
};

/** 看板跳明细时统一带上区间并标记来源，便于明细页显示“返回看板”。 */
const back = true;

export function IssueStatusPanel({ items, period }) {
  const total = (items || []).reduce((sum, item) => sum + item.value, 0);
  return (
    <section className="card">
      <div className="card-title">
        <h3>问题整改状态分布</h3>
        <Link className="hint" to={buildIssueLink({ ...period, back })}>
          查看全部 →
        </Link>
      </div>
      <BarList
        items={(items || []).map((item) => ({
          name: item.name,
          value: item.value,
          color: STATUS_COLORS[item.name] || '#0f766e',
        }))}
        tone="custom"
        emptyText={`${formatRange(period.start, period.end)} 区间内暂无问题数据`}
      />
      {total > 0 ? (
        <div className="card-foot-total">区间内合计 {total} 条</div>
      ) : null}
    </section>
  );
}

export function CategoryPanel({ items, period }) {
  const rows = (items || []).filter((item) => item.total > 0);
  const total = (items || []).reduce((sum, item) => sum + item.total, 0);
  return (
    <section className="card">
      <div className="card-title">
        <h3>问题分类统计</h3>
        <Link className="hint" to={buildIssueLink({ ...period, back })}>
          区间内 {total} 条 · 查看明细 →
        </Link>
      </div>
      <DataTable
        columns={[
          {
            key: 'category',
            title: '问题分类（点击查看明细）',
            render: (row) => (
              <Link to={buildIssueLink({ ...period, category: row.category, back })}>
                {row.category}
              </Link>
            ),
          },
          { key: 'total', title: '累计' },
          { key: 'open', title: '未闭环' },
          { key: 'closed', title: '已闭环' },
          {
            key: 'rate',
            title: '闭环率',
            render: (row) =>
              row.total ? `${Math.round((row.closed / row.total) * 100)}%` : '-',
          },
        ]}
        rows={rows}
        rowKey={(row) => row.category}
        emptyText={`${formatRange(period.start, period.end)} 区间内暂无问题数据`}
      />
    </section>
  );
}

export function DistrictPanel({ items, period }) {
  return (
    <section className="card">
      <div className="card-title">
        <h3>区域运行情况</h3>
        <span className="hint">点击区域或数值查看区间明细</span>
      </div>
      <DataTable
        columns={[
          {
            key: 'district',
            title: '区域（点击查看明细）',
            render: (row) => (
              <Link to={buildIssueLink({ ...period, district: row.district, back })}>
                {row.district}
              </Link>
            ),
          },
          { key: 'restroom_count', title: '公厕数' },
          {
            key: 'inspection_count',
            title: '巡查次数',
            render: (row) =>
              row.inspection_count > 0 ? (
                <Link to={buildInspectionLink({ ...period, district: row.district, back })}>
                  {row.inspection_count}
                </Link>
              ) : (
                0
              ),
          },
          {
            key: 'issue_total',
            title: '区间问题',
            render: (row) =>
              row.issue_total > 0 ? (
                <Link to={buildIssueLink({ ...period, district: row.district, back })}>
                  {row.issue_total}
                </Link>
              ) : (
                0
              ),
          },
          {
            key: 'issue_open',
            title: '未闭环',
            render: (row) =>
              row.issue_open > 0 ? (
                <Link
                  to={buildIssueLink({
                    ...period,
                    district: row.district,
                    back,
                  })}
                  className="text-danger"
                >
                  {row.issue_open}
                </Link>
              ) : (
                0
              ),
          },
          {
            key: 'avg_score',
            title: '巡查均分',
            render: (row) => (row.avg_score != null ? <ScorePill score={row.avg_score} /> : '—'),
          },
        ]}
        rows={items || []}
        rowKey={(row) => row.district}
        emptyText="暂无区域数据"
      />
    </section>
  );
}

export function RankingPanel({ items, period }) {
  return (
    <section className="card">
      <div className="card-title">
        <h3>重点关注公厕</h3>
        <span className="hint">{formatRange(period.start, period.end)} 区间内有活动</span>
      </div>
      <DataTable
        columns={[
          {
            key: 'name',
            title: '公厕',
            render: (row) => <Link to={`/restrooms/${row.restroom_id}`}>{row.name}</Link>,
          },
          { key: 'district', title: '区域' },
          { key: 'inspection_count', title: '巡查次数' },
          {
            key: 'avg_score',
            title: '均分',
            render: (row) => (row.avg_score != null ? <ScorePill score={row.avg_score} /> : '—'),
          },
          { key: 'open_issues', title: '未闭环' },
        ]}
        rows={items || []}
        rowKey={(row) => row.restroom_id}
        emptyText="区间内暂无巡查或问题活动"
      />
    </section>
  );
}

export function RecentIssuesPanel({ items, period }) {
  return (
    <section className="card">
      <div className="card-title">
        <h3>区间最新问题上报</h3>
        <Link className="hint" to={buildIssueLink({ ...period, back })}>
          查看全部 →
        </Link>
      </div>
      <DataTable
        columns={[
          {
            key: 'title',
            title: '问题',
            wrap: true,
            render: (row) => <Link to={`/issues/${row.id}`}>{row.title}</Link>,
          },
          { key: 'restroom', title: '公厕', render: (row) => row.restroom?.name ?? '-' },
          { key: 'severity', title: '程度', render: (row) => <SeverityTag severity={row.severity} /> },
          { key: 'status', title: '状态', render: (row) => <StatusTag status={row.status} /> },
          { key: 'report_time', title: '上报时间', render: (row) => formatDateTime(row.report_time) },
        ]}
        rows={items || []}
        emptyText={`${formatRange(period.start, period.end)} 区间内暂无问题`}
      />
    </section>
  );
}

export function RecentInspectionsPanel({ items, period }) {
  return (
    <section className="card">
      <div className="card-title">
        <h3>区间最新巡查记录</h3>
        <Link className="hint" to={buildInspectionLink({ ...period, back })}>
          查看全部 →
        </Link>
      </div>
      <DataTable
        columns={[
          { key: 'restroom', title: '公厕', render: (row) => row.restroom?.name ?? '-' },
          { key: 'inspector', title: '巡查人' },
          { key: 'shift', title: '班次' },
          { key: 'score', title: '得分', render: (row) => <ScorePill score={row.score} /> },
          { key: 'result', title: '结论', render: (row) => <StatusTag status={row.result} /> },
          { key: 'inspect_time', title: '巡查时间', render: (row) => formatDateTime(row.inspect_time) },
        ]}
        rows={items || []}
        emptyText={`${formatRange(period.start, period.end)} 区间内暂无巡查记录`}
      />
    </section>
  );
}
