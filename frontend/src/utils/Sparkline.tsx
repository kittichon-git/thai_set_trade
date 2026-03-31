// Sparkline.tsx — Inline SVG mini chart for price history
import { memo } from 'react';

interface Props {
  data: number[];
  width?: number;
  height?: number;
  showArea?: boolean;
  showDots?: boolean;
}

const Sparkline = memo(({ data, width = 48, height = 20, showArea = false, showDots = false }: Props) => {
  if (!data || data.length < 2) {
    return <span className="text-slate-600 text-xs">—</span>;
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pad = showArea ? 4 : 1;

  const points = data.map((v, i) => ({
    x: (i / (data.length - 1)) * (width - pad * 2) + pad,
    y: height - pad - ((v - min) / range) * (height - pad * 2),
  }));

  const pts = points.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const isUp = data[data.length - 1] >= data[0];
  const color = isUp ? '#10b981' : '#ef4444';
  const areaColor = isUp ? '#10b98122' : '#ef444422';

  const areaPath = showArea
    ? `M${points[0].x},${height - pad} ` +
      points.map(p => `L${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') +
      ` L${points[points.length - 1].x},${height - pad} Z`
    : '';

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="inline-block"
      aria-hidden="true"
    >
      {showArea && <path d={areaPath} fill={areaColor} />}
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth={showArea ? 2 : 1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {showDots && points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={2.5} fill={color} opacity={0.8}>
          <title>฿{data[i].toFixed(2)}</title>
        </circle>
      ))}
    </svg>
  );
});

Sparkline.displayName = 'Sparkline';
export default Sparkline;
