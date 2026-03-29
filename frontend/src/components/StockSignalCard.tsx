// StockSignalCard.tsx — Mobile stock signal card with expandable DW list
import { memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { StockSignal } from '../types';
import { formatVolume, formatPrice } from '../utils/format';
import VolumeRatioBadge from './VolumeRatioBadge';
import PriceChange from './PriceChange';
import Sparkline from '../utils/Sparkline';
import DWMatchedCard from './DWMatchedCard';

interface Props {
  signal: StockSignal;
  rank: number;
  isExpanded: boolean;
  onToggle: () => void;
}

const borderColorMap: Record<StockSignal['strength'], string> = {
  '5x+': 'border-red-500',
  '3x+': 'border-orange-500',
  '2x+': 'border-yellow-500',
};

const StockSignalCard = memo(({ signal, rank, isExpanded, onToggle }: Props) => {
  const borderColor = borderColorMap[signal.strength];

  return (
    <div
      className={`mb-3 rounded-xl bg-slate-900/70 border border-slate-800/60 border-l-4 ${borderColor} overflow-hidden`}
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

      {/* Expandable DW list */}
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
              <DWMatchedCard dwList={signal.dw_list} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});

StockSignalCard.displayName = 'StockSignalCard';
export default StockSignalCard;
