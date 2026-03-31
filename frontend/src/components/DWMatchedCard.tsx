// DWMatchedCard.tsx — Mobile DW items card list with filter
import { memo, useState, useMemo } from 'react';
import type { DWItem } from '../types';
import { formatVolume } from '../utils/format';

interface Props {
  dwList: DWItem[];
}

type FilterType = 'all' | 'Call' | 'Put';

const DWMatchedCard = memo(({ dwList }: Props) => {
  const [filter, setFilter] = useState<FilterType>('all');

  const filtered = useMemo(() => {
    return filter === 'all' ? dwList : dwList.filter((d) => d.dw_type === filter);
  }, [dwList, filter]);

  const callCount = dwList.filter((d) => d.dw_type === 'Call').length;
  const putCount = dwList.filter((d) => d.dw_type === 'Put').length;

  return (
    <div className="mt-3">
      {/* Filter pill buttons */}
      <div className="flex gap-2 mb-3 flex-wrap">
        {(
          [
            { key: 'all' as FilterType, label: `ทั้งหมด (${dwList.length})` },
            { key: 'Call' as FilterType, label: `Call (${callCount})` },
            { key: 'Put' as FilterType, label: `Put (${putCount})` },
          ] as { key: FilterType; label: string }[]
        ).map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors touch-target ${
              filter === key
                ? 'bg-slate-600 text-white'
                : 'bg-slate-800/80 text-slate-400 hover:bg-slate-700'
            }`}
          >
            {key === 'Call' && '📈 '}
            {key === 'Put' && '📉 '}
            {label}
          </button>
        ))}
      </div>

      {/* DW cards */}
      <div className="flex flex-col gap-2">
        {filtered.length === 0 && (
          <p className="text-slate-500 text-sm text-center py-3">
            ไม่มี DW ในประเภทนี้
          </p>
        )}
        {filtered.map((dw) => (
          <div
            key={dw.dw_code}
            className={`rounded-lg px-3 py-2.5 border-l-4 ${
              dw.dw_type === 'Call'
                ? 'border-blue-500 bg-blue-950/40'
                : 'border-red-500 bg-red-950/40'
            }`}
          >
            {/* Header row */}
            <div className="flex justify-between items-start gap-2">
              <span className="font-mono font-bold text-slate-100 text-sm">{dw.dw_code}</span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${
                  dw.dw_type === 'Call'
                    ? 'bg-blue-900/60 text-blue-300'
                    : 'bg-red-900/60 text-red-300'
                }`}
              >
                {dw.dw_type === 'Call' ? '📈 Call' : '📉 Put'}
              </span>
            </div>

            {/* Detail rows */}
            <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs">
              <span className="text-slate-500">ผู้ออก</span>
              <span className="text-slate-300">{dw.issuer}</span>

              <span className="text-slate-500">ราคา</span>
              <span className="text-slate-200 num font-medium">฿{dw.dw_price.toFixed(2)}</span>

              <span className="text-slate-500">Moneyness</span>
              <span className="text-slate-300">{dw.moneyness}</span>

              <span className="text-slate-500">Volume</span>
              <span className={`num font-semibold ${dw.dw_volume > 0 ? 'text-emerald-400' : 'text-slate-500'}`}>
                {dw.dw_volume > 0 ? formatVolume(dw.dw_volume) : '—'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});

DWMatchedCard.displayName = 'DWMatchedCard';
export default DWMatchedCard;
