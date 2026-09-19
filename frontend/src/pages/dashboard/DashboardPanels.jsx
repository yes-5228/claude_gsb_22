import { Link } from 'react-router-dom';

import BarList from '../../components/BarList.jsx';
import DataTable from '../../components/DataTable.jsx';
import { ScorePill, SeverityTag, StatusTag } from '../../components/Tags.jsx';
import { drillToInspections, drillToIssues } from '../../utils/dashboardRange.js';
import { formatDateTime } from '../../utils/format.js';

const STATUS_COLORS = {
  待整改: '#dc2626',
  整改中: '#d97706',
  待验收: '#2563eb',
  已完成: '#15803d',
  已关闭: '#94a3b8',
};

export function IssueStatusPanel({ items, range }) {
  return (
    <section className="card">
      <div className="card-title">
        <h3>问题整改状态分布</h3>
        <Link className="hint" to={drillToIssues(range)}>
          查看区间全部 →
        </Link>
      </div>
      <BarList
        emptyText="该区间暂无问题上报"
        items={items.map((item) => ({
          name: item.name,
          value: item.value,
          color: STATUS_COLORS[item.name] || '#0f766e',
          to: drillToIssues(range, { status: item.name }),
        }))}
        tone="custom"
      />
    </section>
  );
}

export function CategoryPanel({ items, range }) {
  const rows = (items || []).filter((item) => item.total > 0);
  return (
    <section className="card">
      <div className="card-title">
        <h3>问题分类统计</h3>
        <span className="hint">点击分类查看区间明细</span>
      </div>
      <DataTable
        columns={[
          {
            key: 'category',
            title: '问题分类',
            render: (row) => (
              <Link to={drillToIssues(range, { category: row.category })}>{row.category}</Link>
            ),
          },
          {
            key: 'total',
            title: '区间累计',
            render: (row) => (
              <Link className="btn-link" to={drillToIssues(range, { category: row.category })}>
                {row.total}
              </Link>
            ),
          },
          {
            key: 'open',
            title: '未闭环',
            render: (row) =>
              row.open > 0 ? (
                <Link
                  className="btn-link"
                  to={drillToIssues(range, { category: row.category, open_only: 'true' })}
                >
                  {row.open}
                </Link>
              ) : (
                0
              ),
          },
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
        emptyText="该区间暂无问题上报"
      />
    </section>
  );
}

export function DistrictPanel({ items, range }) {
  return (
    <section className="card">
      <div className="card-title">
        <h3>区域运行情况</h3>
        <span className="hint">点击区域 / 数量查看区间明细</span>
      </div>
      <DataTable
        columns={[
          {
            key: 'district',
            title: '区域',
            render: (row) => (
              <Link to={drillToIssues(range, { district: row.district })}>{row.district}</Link>
            ),
          },
          { key: 'restroom_count', title: '公厕数' },
          {
            key: 'inspection_count',
            title: '区间巡查',
            render: (row) =>
              row.inspection_count > 0 ? (
                <Link
                  className="btn-link"
                  to={drillToInspections(range, { district: row.district })}
                >
                  {row.inspection_count}
                </Link>
              ) : (
                <span className="text-muted">0</span>
              ),
          },
          {
            key: 'issue_count',
            title: '区间问题',
            render: (row) =>
              row.issue_count > 0 ? (
                <Link className="btn-link" to={drillToIssues(range, { district: row.district })}>
                  {row.issue_count}
                </Link>
              ) : (
                <span className="text-muted">0</span>
              ),
          },
          {
            key: 'issue_open',
            title: '未闭环',
            render: (row) =>
              row.issue_open > 0 ? (
                <Link
                  className="btn-link danger"
                  to={drillToIssues(range, { district: row.district, open_only: 'true' })}
                >
                  {row.issue_open}
                </Link>
              ) : (
                <span className="text-muted">0</span>
              ),
          },
          {
            key: 'avg_score',
            title: '区间均分',
            render: (row) =>
              row.avg_score !== null && row.avg_score !== undefined ? (
                <ScorePill score={row.avg_score} />
              ) : (
                <span className="text-muted">无数据</span>
              ),
          },
        ]}
        rows={items || []}
        rowKey={(row) => row.district}
        emptyText="暂无区域数据"
      />
    </section>
  );
}

export function RankingPanel({ items }) {
  return (
    <section className="card">
      <div className="card-title">
        <h3>重点关注公厕</h3>
        <span className="hint">区间内未闭环问题多、均分偏低</span>
      </div>
      <DataTable
        columns={[
          {
            key: 'name',
            title: '公厕',
            render: (row) => <Link to={`/restrooms/${row.restroom_id}`}>{row.name}</Link>,
          },
          { key: 'district', title: '区域' },
          { key: 'inspection_count', title: '区间巡查' },
          {
            key: 'avg_score',
            title: '区间均分',
            render: (row) =>
              row.avg_score !== null && row.avg_score !== undefined ? (
                <ScorePill score={row.avg_score} />
              ) : (
                <span className="text-muted">无数据</span>
              ),
          },
          { key: 'open_issues', title: '未闭环' },
        ]}
        rows={items || []}
        rowKey={(row) => row.restroom_id}
        emptyText="暂无数据"
      />
    </section>
  );
}

export function RecentIssuesPanel({ items, range }) {
  return (
    <section className="card">
      <div className="card-title">
        <h3>区间最新问题</h3>
        <Link className="hint" to={drillToIssues(range)}>
          查看区间全部 →
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
        emptyText="该区间暂无问题上报"
      />
    </section>
  );
}

export function RecentInspectionsPanel({ items, range }) {
  return (
    <section className="card">
      <div className="card-title">
        <h3>区间最新巡查</h3>
        <Link className="hint" to={drillToInspections(range)}>
          查看区间全部 →
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
        emptyText="该区间暂无巡查记录"
      />
    </section>
  );
}
