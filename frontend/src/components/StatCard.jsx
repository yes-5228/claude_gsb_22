import { isValidElement } from 'react';

export default function StatCard({ label, value, unit, foot, tone = 'primary' }) {
  return (
    <div className={`stat-card${tone === 'primary' ? '' : ` is-${tone}`}`}>
      <div className="label">{label}</div>
      <div className="value">
        {value}
        {unit ? <span className="unit">{unit}</span> : null}
      </div>
      {/* foot 传字符串时按默认脚注渲染；传 React 节点时直接渲染（可带涨跌样式） */}
      {foot ? (
        isValidElement(foot) ? (
          foot
        ) : (
          <div className="foot">{foot}</div>
        )
      ) : null}
    </div>
  );
}
