// DWMatchedTable.tsx — Desktop/tablet DW items table with sort + buy
import { memo, useState, useMemo } from 'react';
import type { DWItem } from '../types';
import { formatVolume } from '../utils/format';

interface Props {
  dwList: DWItem[];
  selectedSymbol: string;
  apiUrl: string;
}

type SortKey = 'dw_code' | 'dw_type' | 'issuer' | 'dw_price' | 'dw_volume';
type SortDir = 'asc' | 'desc';

interface BuyState {
  dw_code: string;
  qty: string;
}

const DWMatchedTable = memo(({ dwList, selectedSymbol, apiUrl }: Props) => {
  const [sortKey, setSortKey] = useState<SortKey>('dw_volume');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [buyState, setBuyState] = useState<BuyState | null>(null);
  const [buyResult, setBuyResult] = useState<{ dw_code: string; ok: boolean; msg: string } | null>(null);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir(key === 'dw_volume' ? 'desc' : 'asc');
    }
  };

  const sorted = useMemo(() => {
    return [...dwList].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      let cmp = 0;
      if (typeof av === 'number' && typeof bv === 'number') {
        cmp = av - bv;
      } else {
        cmp = String(av).localeCompare(String(bv));
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [dwList, sortKey, sortDir]);

  const SortIndicator = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return <span className="text-slate-600 ml-0.5">↕</span>;
    return <span className="text-slate-300 ml-0.5">{sortDir === 'asc' ? '↑' : '↓'}</span>;
  };

  const handleBuyClick = (dw_code: string) => {
    setBuyState(buyState?.dw_code === dw_code ? null : { dw_code, qty: '1' });
  };

  const handleConfirm = async (dw: DWItem) => {
    const volume = parseFloat(buyState?.qty ?? '0');
    if (!volume || volume <= 0 || volume % 100 !== 0) {
      setBuyResult({ dw_code: dw.dw_code, ok: false, msg: 'จำนวนต้องเป็นทวีคูณของ 100' });
      setBuyState(null);
      return;
    }
    setBuyResult(null);
    try {
      const res = await fetch(`${apiUrl}/trade/buy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dw_code: dw.dw_code, volume }),
      });
      const data = await res.json();
      if (data.success) {
        setBuyResult({ dw_code: dw.dw_code, ok: true, msg: `ซื้อสำเร็จ Order#${data.order} vol=${data.volume} @ ฿${data.price?.toFixed(4)}` });
      } else {
        setBuyResult({ dw_code: dw.dw_code, ok: false, msg: data.error ?? 'ไม่สำเร็จ' });
      }
    } catch (err) {
      setBuyResult({ dw_code: dw.dw_code, ok: false, msg: 'เชื่อมต่อ backend ไม่ได้' });
    }
    setBuyState(null);
  };

  const thClass =
    'text-left text-xs font-semibold text-slate-400 uppercase tracking-wide py-2 px-2 cursor-pointer select-none hover:text-slate-200 whitespace-nowrap';

  return (
    <div className="slide-down mt-2">
      <div className="text-xs text-slate-500 mb-2">
        DW สำหรับ <span className="text-slate-300 font-medium">{selectedSymbol}</span>
        <span className="ml-1 text-slate-600">({dwList.length} รายการ)</span>
      </div>

      {/* Order result notification */}
      {buyResult && (
        <div className={`mb-2 px-3 py-2 rounded-lg text-xs flex items-center justify-between ${
          buyResult.ok ? 'bg-emerald-900/40 border border-emerald-700/50 text-emerald-300' : 'bg-red-900/40 border border-red-700/50 text-red-300'
        }`}>
          <span>{buyResult.ok ? '✓' : '✕'} {buyResult.msg}</span>
          <button onClick={() => setBuyResult(null)} className="ml-2 opacity-60 hover:opacity-100">✕</button>
        </div>
      )}

      {/* Table */}
      <div className="table-scroll rounded-lg border border-slate-700/50">
        <table className="w-full text-sm">
          <thead className="bg-slate-800/80">
            <tr>
              <th className={thClass} onClick={() => handleSort('dw_code')}>
                DW Code <SortIndicator col="dw_code" />
              </th>
              <th className={thClass} onClick={() => handleSort('issuer')}>
                ผู้ออก <SortIndicator col="issuer" />
              </th>
              <th className={`${thClass} text-right`} onClick={() => handleSort('dw_price')}>
                ราคา฿ <SortIndicator col="dw_price" />
              </th>
              <th className={`${thClass} text-right`} onClick={() => handleSort('dw_volume')}>
                Volume <SortIndicator col="dw_volume" />
              </th>
              <th className="text-center text-xs font-semibold text-slate-400 uppercase tracking-wide py-2 px-2 whitespace-nowrap">
                ซื้อ
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 && (
              <tr>
                <td colSpan={5} className="text-center text-slate-500 py-6 text-sm">
                  ไม่มี DW ที่ตรงตามเงื่อนไข
                </td>
              </tr>
            )}
            {sorted.map((dw) => {
              const isBuying = buyState?.dw_code === dw.dw_code;
              return (
                <tr
                  key={dw.dw_code}
                  className={`border-t border-slate-700/30 transition-colors hover:bg-slate-700/20 ${
                    dw.dw_type === 'Call' ? 'bg-blue-950/40' : 'bg-red-950/40'
                  }`}
                >
                  <td className="py-2 px-2 font-mono font-semibold text-slate-200 text-xs">
                    {dw.dw_code}
                  </td>
                  <td className="py-2 px-2 text-slate-300 text-xs">{dw.issuer}</td>
                  <td className="py-2 px-2 text-right num text-slate-200 text-xs">
                    {dw.dw_price.toFixed(2)}
                  </td>
                  <td className="py-2 px-2 text-right num text-xs">
                    <span className={dw.dw_volume > 0 ? 'text-emerald-400 font-semibold' : 'text-slate-500'}>
                      {dw.dw_volume > 0 ? formatVolume(dw.dw_volume) : '—'}
                    </span>
                  </td>
                  <td className="py-2 px-2 text-center">
                    {isBuying ? (
                      <div className="flex items-center gap-1 justify-center">
                        <input
                          type="number"
                          min="100"
                          step="100"
                          placeholder="100"
                          value={buyState.qty}
                          onChange={(e) => setBuyState({ ...buyState, qty: e.target.value })}
                          onClick={(e) => e.stopPropagation()}
                          className="w-20 text-xs bg-slate-700 border border-slate-600 text-slate-100 rounded px-1.5 py-1 num text-center focus:outline-none focus:ring-1 focus:ring-emerald-500"
                        />
                        <span className="text-[10px] text-slate-500">หุ้น</span>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleConfirm(dw); }}
                          className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white px-2 py-1 rounded transition-colors font-medium"
                        >
                          ยืนยัน
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); setBuyState(null); }}
                          className="text-xs text-slate-500 hover:text-slate-300 px-1 py-1 transition-colors"
                        >
                          ✕
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleBuyClick(dw.dw_code); }}
                        className="text-xs bg-slate-700 hover:bg-emerald-700 text-slate-300 hover:text-white px-2.5 py-1 rounded transition-colors font-medium"
                      >
                        Buy
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
});

DWMatchedTable.displayName = 'DWMatchedTable';
export default DWMatchedTable;
