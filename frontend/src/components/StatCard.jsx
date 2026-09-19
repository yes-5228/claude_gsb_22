export default function StatCard({ label, value, unit, foot, tone = 'primary' }) {
  const isEmpty = value === null || value === undefined;
  return (
    <div className={`stat-card${tone === 'primary' ? '' : ` is-${tone}`}`}>
      <div className="label">{label}</div>
      <div className={`value${isEmpty ? ' is-empty' : ''}`}>
        {isEmpty ? '无数据' : value}
        {!isEmpty && unit ? <span className="unit">{unit}</span> : null}
      </div>
      {foot ? <div className="foot">{foot}</div> : null}
    </div>
  );
}
