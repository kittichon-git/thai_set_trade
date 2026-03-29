// StockSignalTable.tsx — Desktop/tablet signal table with accordion DW expansion
import { memo, useState, useCallback, useRef, useEffect } from 'react';
import type { StockSignal } from '../types';
import { formatVolume, formatPrice } from '../utils/format';
import VolumeRatioBadge from './VolumeRatioBadge';
import PriceChange from './PriceChange';
import Sparkline from '../utils/Sparkline';
import DWMatchedTable from './DWMatchedTable';

interface Props {
  signals: StockSignal[];
  breakpoint: 'mobile' | 'tablet' | 'desktop';
}

interface RowProps {
  signal: StockSignal;
  rank: number;
  isExpanded: boolean;
  onToggle: () => void;
  breakpoint: 'mobile' | 'tablet' | 'desktop';
  prevRatio?: number;
}

const SignalRow = memo(({ signal, rank, isExpanded, onToggle, breakpoint, prevRatio }: RowProps) => {
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
                signal.strength === '5x+'
                  ? 'bg-red-500'
                  : signal.strength === '3x+'
                  ? 'bg-orange-500'
                  : 'bg-yellow-500'
              }`}
            />
            <div>
              <div className="font-bold text-slate-100 text-sm tracking-wide">
                {signal.symbol}
              </div>
              <div className="text-xs text-slate-500 num">
                {signal.dw_list.length} DW
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
          {formatVolume(signal.today_volume)}
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

        {/* Sparkline */}
        <td className="py-3 px-2 text-center">
          <Sparkline data={signal.sparkline} width={48} height={20} />
        </td>

        {/* DW count + expand toggle */}
        <td className="py-3 px-3 text-right">
          <button
            className="text-xs text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-1 ml-auto"
            onClick={(e) => { e.stopPropagation(); onToggle(); }}
            aria-label={isExpanded ? 'Collapse DW list' : 'Expand DW list'}
          >
            <span>DW {signal.dw_list.length}</span>
            <span
              className={`transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
            >
              ▾
            </span>
          </button>
        </td>
      </tr>

      {/* Accordion: DW matched table */}
      {isExpanded && (
        <tr>
          <td
            colSpan={isDesktop ? 9 : 8}
            className="bg-slate-900/60 px-4 py-4 border-t border-slate-700/40"
          >
            <DWMatchedTable dwList={signal.dw_list} selectedSymbol={signal.symbol} />
          </td>
        </tr>
      )}
    </>
  );
});

SignalRow.displayName = 'SignalRow';

const StockSignalTable = memo(({ signals, breakpoint }: Props) => {
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
    <div className="fade-in">
      <div className="mb-3 flex items-center gap-2">
        <span className="text-slate-400 text-sm font-medium">🔥 Volume Anomaly — Top 10</span>
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
              <th className="text-center text-xs font-semibold text-slate-500 uppercase tracking-wide py-3 px-2">
                Spark
              </th>
              <th className="text-right text-xs font-semibold text-slate-500 uppercase tracking-wide py-3 px-3">
                DW
              </th>
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
