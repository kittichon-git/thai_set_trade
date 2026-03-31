// CandlestickChart.tsx — TradingView-style price + volume chart
import { useEffect, useRef, memo } from 'react';
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  ColorType,
  LineStyle,
} from 'lightweight-charts';
import type { OHLCBar } from '../types';
import { formatVolume } from '../utils/format';

interface Props {
  data: OHLCBar[];
  height?: number;
}

// TradingView-like color palette
const UP_COLOR    = '#089981';
const DOWN_COLOR  = '#f23645';
const UP_VOL      = 'rgba(8,153,129,0.45)';
const DOWN_VOL    = 'rgba(242,54,69,0.45)';
const GRID_COLOR  = '#1e293b';
const BORDER_COLOR = '#334155';
const TEXT_COLOR  = '#64748b';
const BG          = 'transparent';

const CandlestickChart = memo(({ data, height = 160 }: Props) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const lastVol = data.length > 0 ? data[data.length - 1].volume ?? 0 : 0;
  const hasVolume = data.some(d => (d.volume ?? 0) > 0);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || data.length === 0) return;

    const chart = createChart(el, {
      width: el.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: BG },
        textColor: TEXT_COLOR,
        fontSize: 11,
        fontFamily: "'Inter','ui-monospace',monospace",
      },
      grid: {
        vertLines: { color: GRID_COLOR, style: LineStyle.Solid },
        horzLines: { color: GRID_COLOR, style: LineStyle.Dotted },
      },
      timeScale: {
        borderColor: BORDER_COLOR,
        timeVisible: true,
        secondsVisible: false,
        fixLeftEdge: true,
        fixRightEdge: true,
        tickMarkFormatter: (time: number) => {
          const d = new Date(time * 1000);
          return `${d.getDate()}/${d.getMonth() + 1}`;
        },
      },
      rightPriceScale: {
        borderColor: BORDER_COLOR,
        textColor: TEXT_COLOR,
        // reserve bottom ~28% for volume
        scaleMargins: { top: 0.05, bottom: 0.28 },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: '#475569',
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: '#1e293b',
        },
        horzLine: {
          color: '#475569',
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: '#1e293b',
        },
      },
      handleScale: false,
      handleScroll: false,
    });

    // ── Candlestick ───────────────────────────────────────────────────────
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor:        UP_COLOR,
      downColor:      DOWN_COLOR,
      borderUpColor:  UP_COLOR,
      borderDownColor: DOWN_COLOR,
      wickUpColor:    UP_COLOR,
      wickDownColor:  DOWN_COLOR,
    });

    candleSeries.setData(
      data.map(d => ({ time: d.time, open: d.open, high: d.high, low: d.low, close: d.close }))
    );

    // ── Volume histogram ──────────────────────────────────────────────────
    if (hasVolume) {
      const volSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: 'volume' },
        priceScaleId: 'vol',
      });

      chart.priceScale('vol').applyOptions({
        scaleMargins: { top: 0.76, bottom: 0.02 },
        borderVisible: false,
      });

      volSeries.setData(
        data.map(d => ({
          time: d.time,
          value: d.volume ?? 0,
          color: (d.close >= d.open) ? UP_VOL : DOWN_VOL,
        }))
      );
    }

    chart.timeScale().fitContent();

    const observer = new ResizeObserver(() => {
      chart.applyOptions({ width: el.clientWidth });
      chart.timeScale().fitContent();
    });
    observer.observe(el);

    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [data, height, hasVolume]);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center text-slate-500 text-xs" style={{ height }}>
        ไม่มีข้อมูลกราฟ
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Volume label — top-left (like TradingView) */}
      {hasVolume && lastVol > 0 && (
        <div className="absolute top-1 left-1 z-10 flex items-center gap-1 pointer-events-none">
          <span className="text-[10px] text-slate-500">ปริมาณ</span>
          <span className="text-[10px] font-semibold text-slate-300 num">
            {formatVolume(lastVol)}
          </span>
        </div>
      )}
      <div ref={containerRef} style={{ width: '100%', height }} />
    </div>
  );
});

CandlestickChart.displayName = 'CandlestickChart';
export default CandlestickChart;
