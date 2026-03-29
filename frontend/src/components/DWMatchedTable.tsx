// DWMatchedTable.tsx — Desktop/tablet DW items table with filter + sort
import { memo, useState, useMemo } from 'react';
import type { DWItem } from '../types';
import { formatThaiDate } from '../utils/format';

interface Props {
  dwList: DWItem[];
  selectedSymbol: string;
}

type FilterType = 'all' | 'Call' | 'Put';
type SortKey = 'dw_code' | 'dw_type' | 'issuer' | 'dw_price' | 'gearing' | 'moneyness' | 'expiry_date' | 'days_remaining';
type SortDir = 'asc' | 'desc';

const DWMatchedTable = memo(({ dwList, selectedSymbol }: Props) => {
  const [filter, setFilter] = useState<FilterType>('all');
  const [sortKey, setSortKey] = useState<SortKey>('gearing');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const filtered = useMemo(() => {
    const base = filter === 'all' ? dwList : dwList.filter((d) => d.dw_type === filter);
    return [...base].sort((a, b) => {
      let cmp = 0;
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === 'number' && typeof bv === 'number') {
        cmp = av - bv;
      } else {
        cmp = String(av).localeCompare(String(bv));
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [dwList, filter, sortKey, sortDir]);

  const SortIndicator = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return <span className="text-slate-600 ml-0.5">↕</span>;
    return <span className="text-slate-300 ml-0.5">{sortDir === 'asc' ? '↑' : '↓'}</span>;
  };

  const thClass =
    'text-left text-xs font-semibold text-slate-400 uppercase tracking-wide py-2 px-2 cursor-pointer select-none hover:text-slate-200 whitespace-nowrap';

  return (
    <div className="slide-down mt-2">
      {/* Filter buttons */}
      <div className="flex gap-2 mb-3 flex-wrap">
        <span className="text-xs text-slate-500 self-center mr-1">
          DW สำหรับ {selectedSymbol}:
        </span>
        {(['all', 'Call', 'Put'] as FilterType[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors touch-target flex items-center gap-1 ${
              filter === f
                ? 'bg-slate-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
            }`}
          >
            {f === 'all' && 'ทั้งหมด'}
            {f === 'Call' && '📈 Call'}
            {f === 'Put' && '📉 Put'}
            {f === 'all' && (
              <span className="bg-slate-500 text-slate-200 rounded-full px-1.5 py-0.5 text-xs">
                {dwList.length}
              </span>
            )}
            {f !== 'all' && (
              <span className="bg-slate-600 text-slate-300 rounded-full px-1.5 py-0.5 text-xs">
                {dwList.filter((d) => d.dw_type === f).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="table-scroll rounded-lg border border-slate-700/50">
        <table className="w-full text-sm">
          <thead className="bg-slate-800/80">
            <tr>
              <th className={thClass} onClick={() => handleSort('dw_code')}>
                DW Code <SortIndicator col="dw_code" />
              </th>
              <th className={thClass} onClick={() => handleSort('dw_type')}>
                ประเภท <SortIndicator col="dw_type" />
              </th>
              <th className={thClass} onClick={() => handleSort('issuer')}>
                ผู้ออก <SortIndicator col="issuer" />
              </th>
              <th className={`${thClass} text-right`} onClick={() => handleSort('dw_price')}>
                ราคา฿ <SortIndicator col="dw_price" />
              </th>
              <th className={`${thClass} text-right`} onClick={() => handleSort('gearing')}>
                อัตราทด <SortIndicator col="gearing" />
              </th>
              {/* Moneyness hidden on tablet — shown only on desktop */}
              <th className={`${thClass} hidden lg:table-cell`} onClick={() => handleSort('moneyness')}>
                Moneyness <SortIndicator col="moneyness" />
              </th>
              <th className={thClass} onClick={() => handleSort('expiry_date')}>
                วันหมดอายุ <SortIndicator col="expiry_date" />
              </th>
              <th className={`${thClass} text-right`} onClick={() => handleSort('days_remaining')}>
                วันเหลือ <SortIndicator col="days_remaining" />
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="text-center text-slate-500 py-6 text-sm">
                  ไม่มี DW ที่ตรงตามเงื่อนไข
                </td>
              </tr>
            )}
            {filtered.map((dw) => (
              <tr
                key={dw.dw_code}
                className={`border-t border-slate-700/30 transition-colors hover:bg-slate-700/20 ${
                  dw.dw_type === 'Call' ? 'bg-blue-950/40' : 'bg-red-950/40'
                }`}
              >
                <td className="py-2 px-2 font-mono font-semibold text-slate-200 text-xs">
                  {dw.dw_code}
                </td>
                <td className="py-2 px-2">
                  <span
                    className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                      dw.dw_type === 'Call'
                        ? 'bg-blue-900/60 text-blue-300'
                        : 'bg-red-900/60 text-red-300'
                    }`}
                  >
                    {dw.dw_type === 'Call' ? '📈 Call' : '📉 Put'}
                  </span>
                </td>
                <td className="py-2 px-2 text-slate-300 text-xs">{dw.issuer}</td>
                <td className="py-2 px-2 text-right num text-slate-200 text-xs">
                  {dw.dw_price.toFixed(2)}
                </td>
                <td className="py-2 px-2 text-right num text-slate-200 text-xs">
                  {dw.gearing.toFixed(2)}x
                </td>
                <td className="py-2 px-2 text-slate-400 text-xs hidden lg:table-cell">
                  {dw.moneyness}
                </td>
                <td className="py-2 px-2 text-slate-300 text-xs num">
                  {formatThaiDate(dw.expiry_date)}
                </td>
                <td className="py-2 px-2 text-right num text-xs">
                  <span
                    className={
                      dw.days_remaining <= 30
                        ? 'text-orange-400 font-semibold'
                        : 'text-slate-400'
                    }
                  >
                    {dw.days_remaining}d
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
});

DWMatchedTable.displayName = 'DWMatchedTable';
export default DWMatchedTable;
