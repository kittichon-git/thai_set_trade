// StockSignalTable.tsx — Desktop/tablet signal table with accordion DW expansion
import { memo, useState, useCallback, useRef, useEffect } from 'react';
import type { StockSignal } from '../types';
import { formatVolume, formatPrice } from '../utils/format';
import VolumeRatioBadge from './VolumeRatioBadge';
import PriceChange from './PriceChange';
import Sparkline from '../utils/Sparkline';
import DWMatchedTable from './DWMatchedTable';
import CandlestickChart from './CandlestickChart';

interface Props {
  title: string;
  icon?: string;
  signals: StockSignal[];
  breakpoint: 'mobile' | 'tablet' | 'desktop';
  apiUrl: string;
}

interface RowProps {
  signal: StockSignal;
  rank: number;
  isExpanded: boolean;
  onToggle: () => void;
  breakpoint: 'mobile' | 'tablet' | 'desktop';
  prevRatio?: number;
  apiUrl: string;
}

const SignalRow = memo(({ signal, rank, isExpanded, onToggle, breakpoint, prevRatio, apiUrl }: RowProps) => {
  const [flashClass, setFlashClass] = useState('');
  const prevRatioRef = useRef(prevRatio);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    const prev = prevRatioRef.current;
    prevRatioRef.current = signal.volume_ratio;
    if (prev !== undefined && prev !== signal.volume_ratio) {
      const cls = signal.volume_ratio > prev ? 'flash-up' : 'flash-down';
      setFlashClass(cls);
      clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setFlashClass(''), 850);
    }
    return () => clearTimeout(timerRef.current);
  }, [signal.volume_ratio]);

  const isDesktop = breakpoint === 'desktop';
  const ohlc = signal.ohlc ?? [];

  return (
    <>
      <tr
        className={`border-t border-slate-800/60 cursor-pointer transition-colors hover:bg-slate-800/40 ${flashClass} ${
          isExpanded ? 'bg-slate-800/30' : ''
        }`}
        onClick={onToggle}
        aria-expanded={isExpanded}
      >
        {/* Rank */}
        <td className="py-3 px-3 text-slate-500 text-sm num w-8">
          {rank}
        </td>

        {/* Symbol */}
        <td className="py-3 px-2">
          <div className="flex items-center gap-2">
            <span
              className={`w-1 h-8 rounded-full flex-shrink-0 ${
                signal.volume_ratio >= 5.0
                  ? 'bg-red-500'
                  : signal.volume_ratio >= 3.0
                  ? 'bg-orange-500'
                  : 'bg-yellow-500'
              }`}
            />
            <div>
              <div className="font-bold text-slate-100 text-sm tracking-wide flex items-center gap-2">
                {signal.symbol}
                {signal.signal_type && (
                  <span className="text-[10px] bg-blue-500/20 text-blue-300 px-1.5 py-0.5 rounded border border-blue-500/30 font-medium">
                    {signal.signal_type}
                  </span>
                )}
              </div>
            </div>
          </div>
        </td>

        {/* Price */}
        <td className="py-3 px-2 num text-slate-200 text-sm text-right">
          ฿{formatPrice(signal.last_price)}
        </td>

        {/* Change % */}
        <td className="py-3 px-2 text-right">
          <PriceChange value={signal.change_pct} />
        </td>

        {/* Volume today */}
        <td className="py-3 px-2 text-right num text-sm text-slate-300">
          <div className="font-medium">{formatVolume(signal.today_volume)}</div>
          {signal.signal_value > 1000 && (
             <div className="text-[10px] text-slate-500">
               {formatVolume(signal.signal_value)} ฿
             </div>
          )}
        </td>

        {/* Avg 5d volume (desktop only) */}
        {isDesktop && (
          <td className="py-3 px-2 text-right num text-sm text-slate-500">
            {formatVolume(signal.avg_5d_volume)}
          </td>
        )}

        {/* Volume ratio badge */}
        <td className="py-3 px-2 text-right">
          <VolumeRatioBadge ratio={signal.volume_ratio} strength={signal.strength} />
        </td>

        {/* Expand indicator */}
        <td className="py-3 px-3 text-right">
          <span className={`text-slate-500 text-xs transition-transform duration-200 inline-block ${isExpanded ? 'rotate-180' : ''}`}>▾</span>
        </td>
      </tr>

      {/* Accordion: chart + DW list */}
      {isExpanded && (
        <tr>
          <td
            colSpan={isDesktop ? 7 : 6}
            className="bg-slate-900/60 px-4 py-4 border-t border-slate-700/40 slide-down"
          >
            {/* Price chart */}
            {ohlc.length >= 1 ? (
              <div className="mb-4 bg-slate-800/50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-slate-400 font-medium">{signal.symbol} — แท่งเทียนรายวัน</span>
                  <span className="text-xs num">
                    <span className="text-slate-500">฿{ohlc[0].close.toFixed(2)} → </span>
                    <span className={ohlc[ohlc.length-1].close >= ohlc[0].close ? 'text-emerald-400' : 'text-red-400'}>
                      ฿{ohlc[ohlc.length-1].close.toFixed(2)}
                    </span>
                  </span>
                </div>
                <CandlestickChart data={ohlc} height={160} />
              </div>
            ) : signal.sparkline.length >= 2 ? (
              <div className="mb-4 bg-slate-800/50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-slate-400 font-medium">{signal.symbol} — ราคา 5 วันล่าสุด</span>
                  <span className="text-xs num">
                    <span className="text-slate-500">฿{signal.sparkline[0].toFixed(2)} → </span>
                    <span className={signal.sparkline[signal.sparkline.length-1] >= signal.sparkline[0] ? 'text-emerald-400' : 'text-red-400'}>
                      ฿{signal.sparkline[signal.sparkline.length-1].toFixed(2)}
                    </span>
                  </span>
                </div>
                <Sparkline data={signal.sparkline} width={isDesktop ? 500 : 320} height={72} showArea showDots />
              </div>
            ) : null}
            {/* DW Call list */}
            <div className="text-xs text-slate-500 mb-2 font-medium">
              📋 DW Call ที่เข้าเงื่อนไข — {signal.symbol}
              <span className="ml-2 text-slate-600">({signal.dw_list.length} รายการ เรียงตาม Volume)</span>
            </div>
            <DWMatchedTable dwList={signal.dw_list} selectedSymbol={signal.symbol} apiUrl={apiUrl} />
          </td>
        </tr>
      )}
    </>
  );
});

SignalRow.displayName = 'SignalRow';

const StockSignalTable = memo(({ title, icon = '🔥', signals, breakpoint, apiUrl }: Props) => {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  const handleToggle = useCallback((idx: number) => {
    setExpandedIdx((prev) => (prev === idx ? null : idx));
  }, []);

  const isDesktop = breakpoint === 'desktop';

  if (signals.length === 0) {
    return (
      <div className="fade-in text-center py-16 text-slate-500">
        <div className="text-4xl mb-3">🔍</div>
        <div className="text-base font-medium">ยังไม่พบสัญญาณ</div>
        <div className="text-sm mt-1 text-slate-600">กำลังรอข้อมูล...</div>
      </div>
    );
  }

  return (
    <div className="fade-in mb-8">
      <div className="mb-3 flex items-center gap-2">
        <span className="text-xl">{icon}</span>
        <span className="text-slate-400 text-sm font-medium">{title}</span>
        <span className="bg-slate-800 text-slate-400 text-xs px-2 py-0.5 rounded-full num">
          {signals.length}
        </span>
      </div>

      <div className="table-scroll rounded-xl border border-slate-800/60 bg-slate-900/40">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-800/60">
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide py-3 px-3 w-8">
                #
              </th>
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide py-3 px-2">
                Symbol
              </th>
              <th className="text-right text-xs font-semibold text-slate-500 uppercase tracking-wide py-3 px-2">
                ราคา
              </th>
              <th className="text-right text-xs font-semibold text-slate-500 uppercase tracking-wide py-3 px-2">
                เปลี่ยน
              </th>
              <th className="text-right text-xs font-semibold text-slate-500 uppercase tracking-wide py-3 px-2">
                Vol วันนี้
              </th>
              {isDesktop && (
                <th className="text-right text-xs font-semibold text-slate-500 uppercase tracking-wide py-3 px-2">
                  Avg 5วัน
                </th>
              )}
              <th className="text-right text-xs font-semibold text-slate-500 uppercase tracking-wide py-3 px-2">
                อัตรา
              </th>
              <th className="py-3 px-3 w-6" />
            </tr>
          </thead>
          <tbody>
            {signals.map((sig, idx) => (
              <SignalRow
                key={sig.symbol}
                signal={sig}
                rank={idx + 1}
                isExpanded={expandedIdx === idx}
                onToggle={() => handleToggle(idx)}
                breakpoint={breakpoint}
                apiUrl={apiUrl}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
});

StockSignalTable.displayName = 'StockSignalTable';
export default StockSignalTable;
