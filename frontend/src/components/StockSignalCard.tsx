// StockSignalCard.tsx — Mobile stock signal card with expandable DW list
import { memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { StockSignal } from '../types';
import { formatVolume, formatPrice } from '../utils/format';
import VolumeRatioBadge from './VolumeRatioBadge';
import PriceChange from './PriceChange';
import Sparkline from '../utils/Sparkline';
import DWMatchedCard from './DWMatchedCard';
import CandlestickChart from './CandlestickChart';

interface Props {
  signal: StockSignal;
  rank: number;
  isExpanded: boolean;
  onToggle: () => void;
  apiUrl: string;
}

const StockSignalCard = memo(({ signal, rank, isExpanded, onToggle, apiUrl }: Props) => {
  const borderColor =
    signal.strength === 'High' || signal.volume_ratio >= 5.0
      ? 'border-red-500'
      : signal.volume_ratio >= 3.0
      ? 'border-orange-500'
      : 'border-yellow-500';
  const ohlc = signal.ohlc ?? [];

  return (
    <div
      className={`mb-3 rounded-md bg-slate-900/70 border border-slate-800/60 border-l-4 ${borderColor} overflow-hidden`}
    >
      {/* Card header — tap to expand/collapse */}
      <button
        className="w-full text-left px-3 pt-3 pb-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-500"
        onClick={onToggle}
        aria-expanded={isExpanded}
        aria-label={`${signal.symbol} signal card, rank ${rank}`}
      >
        {/* Row 1: Rank + Symbol + Badge */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-slate-600 text-xs num font-medium w-5 flex-shrink-0">
              #{rank}
            </span>
            <span className="font-bold text-slate-100 text-base tracking-wide truncate">
              {signal.symbol}
            </span>
          </div>
          <VolumeRatioBadge ratio={signal.volume_ratio} strength={signal.strength} />
        </div>

        {/* Row 2: Price + Change + Sparkline */}
        <div className="flex items-center gap-3 mt-1.5">
          <span className="num text-slate-200 font-medium text-sm">
            ฿{formatPrice(signal.last_price)}
          </span>
          <PriceChange value={signal.change_pct} />
          <div className="ml-auto">
            <Sparkline data={signal.sparkline} width={60} height={24} />
          </div>
        </div>

        {/* Row 3: Volume info */}
        <div className="flex items-center gap-1.5 mt-1.5 text-xs text-slate-400 num">
          <span>Vol {formatVolume(signal.today_volume)}</span>
          <span className="text-slate-700">·</span>
          <span>Avg {formatVolume(signal.avg_5d_volume)}</span>
        </div>
      </button>

      {/* DW expand button */}
      <div className="px-3 pb-2">
        <button
          className="w-full mt-1 py-2 px-3 rounded-lg bg-slate-800/60 hover:bg-slate-700/60 text-xs text-slate-400 hover:text-slate-200 transition-colors flex items-center justify-center gap-2 touch-target"
          onClick={onToggle}
          aria-expanded={isExpanded}
        >
          <span>📋 ดู DW {signal.dw_list.length} รายการ</span>
          <motion.span
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            className="inline-block"
          >
            ▼
          </motion.span>
        </button>
      </div>

      {/* Expandable chart + DW list */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            style={{ overflow: 'hidden' }}
          >
            <div className="px-3 pb-3 border-t border-slate-700/40 pt-3">
              {/* Price chart */}
              {ohlc.length >= 1 ? (
                <div className="mb-3 bg-slate-800/50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-slate-400 font-medium">{signal.symbol} — แท่งเทียนรายวัน</span>
                    <span className="text-xs num">
                      <span className="text-slate-500">฿{ohlc[0].close.toFixed(2)} → </span>
                      <span className={ohlc[ohlc.length-1].close >= ohlc[0].close ? 'text-emerald-400' : 'text-red-400'}>
                        ฿{ohlc[ohlc.length-1].close.toFixed(2)}
                      </span>
                    </span>
                  </div>
                  <CandlestickChart data={ohlc} height={208} />
                </div>
              ) : signal.sparkline.length >= 2 ? (
                <div className="mb-3 bg-slate-800/50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-slate-400 font-medium">{signal.symbol} — 5 วันล่าสุด</span>
                    <span className="text-xs num">
                      <span className="text-slate-500">฿{signal.sparkline[0].toFixed(2)} → </span>
                      <span className={signal.sparkline[signal.sparkline.length-1] >= signal.sparkline[0] ? 'text-emerald-400' : 'text-red-400'}>
                        ฿{signal.sparkline[signal.sparkline.length-1].toFixed(2)}
                      </span>
                    </span>
                  </div>
                  <Sparkline data={signal.sparkline} width={280} height={83} showArea showDots />
                </div>
              ) : null}
              {/* DW Call list */}
              <div className="text-xs text-slate-500 mb-2 font-medium">
                📋 DW Call — {signal.symbol} ({signal.dw_list.length} รายการ)
              </div>
              <DWMatchedCard dwList={signal.dw_list} apiUrl={apiUrl} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});

StockSignalCard.displayName = 'StockSignalCard';
export default StockSignalCard;
