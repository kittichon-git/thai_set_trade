// DWMatchedCard.tsx — Mobile DW items list with Buy button
import { memo, useState } from 'react';
import type { DWItem } from '../types';
import { formatVolume } from '../utils/format';

interface Props {
  dwList: DWItem[];
  apiUrl: string;
}

interface BuyState {
  dw_code: string;
  qty: string;
}

const DWMatchedCard = memo(({ dwList, apiUrl }: Props) => {
  const [buyState, setBuyState] = useState<BuyState | null>(null);
  const [buyResult, setBuyResult] = useState<{ dw_code: string; ok: boolean; msg: string } | null>(null);

  const handleBuyClick = (dw_code: string) => {
    setBuyState(buyState?.dw_code === dw_code ? null : { dw_code, qty: '100' });
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
    } catch {
      setBuyResult({ dw_code: dw.dw_code, ok: false, msg: 'เชื่อมต่อ backend ไม่ได้' });
    }
    setBuyState(null);
  };

  return (
    <div className="mt-3">
      {/* Order result notification */}
      {buyResult && (
        <div className={`mb-2 px-3 py-2 rounded text-xs flex items-center justify-between ${
          buyResult.ok ? 'bg-emerald-900/40 border border-emerald-700/50 text-emerald-300' : 'bg-red-900/40 border border-red-700/50 text-red-300'
        }`}>
          <span>{buyResult.ok ? '✓' : '✕'} {buyResult.msg}</span>
          <button onClick={() => setBuyResult(null)} className="ml-2 opacity-60 hover:opacity-100">✕</button>
        </div>
      )}

      {/* DW cards */}
      <div className="flex flex-col gap-2">
        {dwList.length === 0 && (
          <p className="text-slate-500 text-sm text-center py-3">ไม่มี DW</p>
        )}
        {dwList.map((dw) => {
          const isBuying = buyState?.dw_code === dw.dw_code;
          return (
            <div
              key={dw.dw_code}
              className={`rounded px-3 py-2.5 border-l-4 ${
                dw.dw_type === 'Call'
                  ? 'border-blue-500 bg-blue-950/40'
                  : 'border-red-500 bg-red-950/40'
              }`}
            >
              {/* Header row */}
              <div className="flex justify-between items-center gap-2">
                <span className="font-mono font-bold text-slate-100 text-sm">{dw.dw_code}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium flex-shrink-0 ${
                  dw.dw_type === 'Call' ? 'bg-blue-900/60 text-blue-300' : 'bg-red-900/60 text-red-300'
                }`}>
                  {dw.dw_type === 'Call' ? '📈 Call' : '📉 Put'}
                </span>
              </div>

              {/* Detail rows */}
              <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs">
                <span className="text-slate-500">ผู้ออก</span>
                <span className="text-slate-300">{dw.issuer}</span>

                <span className="text-slate-500">ราคา</span>
                <span className="text-slate-200 num font-medium">฿{dw.dw_price.toFixed(2)}</span>

                <span className="text-slate-500">Volume</span>
                <span className={`num font-semibold ${dw.dw_volume > 0 ? 'text-emerald-400' : 'text-slate-500'}`}>
                  {dw.dw_volume > 0 ? formatVolume(dw.dw_volume) : '—'}
                </span>
              </div>

              {/* Buy section */}
              <div className="mt-2.5 pt-2 border-t border-slate-700/40">
                {isBuying ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min="100"
                      step="100"
                      placeholder="100"
                      value={buyState.qty}
                      onChange={(e) => setBuyState({ ...buyState, qty: e.target.value })}
                      className="flex-1 text-xs bg-slate-700 border border-slate-600 text-slate-100 rounded px-2 py-1.5 num text-center focus:outline-none focus:ring-1 focus:ring-emerald-500"
                    />
                    <span className="text-[10px] text-slate-500">หุ้น</span>
                    <button
                      onClick={() => handleConfirm(dw)}
                      className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded transition-colors font-medium"
                    >
                      ยืนยัน
                    </button>
                    <button
                      onClick={() => setBuyState(null)}
                      className="text-xs text-slate-500 hover:text-slate-300 px-1.5 py-1.5 transition-colors"
                    >
                      ✕
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => handleBuyClick(dw.dw_code)}
                    className="w-full text-xs bg-slate-700 hover:bg-emerald-700 text-slate-300 hover:text-white py-1.5 rounded transition-colors font-medium"
                  >
                    Buy
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});

DWMatchedCard.displayName = 'DWMatchedCard';
export default DWMatchedCard;
