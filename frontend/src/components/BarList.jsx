import { Link } from 'react-router-dom';

export default function BarList({ items, tone = 'primary', emptyText = '暂无数据' }) {
  const max = Math.max(...items.map((item) => item.value), 1);
  if (!items.length) return <div className="empty-block">{emptyText}</div>;

  return (
    <div className="bar-list">
      {items.map((item) => {
        const content = (
          <>
            <span title={item.name}>{item.name}</span>
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{
                  width: `${(item.value / max) * 100}%`,
                  background: tone === 'primary' ? undefined : item.color,
                }}
              />
            </div>
            <span className="bar-value">{item.value}</span>
          </>
        );
        // 值为 0 的行不下钻（该口径下没有明细可看）
        return item.to && item.value > 0 ? (
          <Link className="bar-row is-link" to={item.to} key={item.name} title="点击查看明细">
            {content}
          </Link>
        ) : (
          <div className="bar-row" key={item.name}>
            {content}
          </div>
        );
      })}
    </div>
  );
}
