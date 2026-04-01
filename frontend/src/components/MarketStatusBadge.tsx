// MarketStatusBadge.tsx — Market open/closed status indicator
import { memo } from 'react';

interface Props {
  status: string;
}

const MarketStatusBadge = memo(({ status }: Props) => {
  if (status === 'OPEN') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold bg-emerald-900/70 text-emerald-300 border border-emerald-700/50">
        <span className="live-dot inline-block w-2 h-2 rounded-full bg-emerald-400" />
        OPEN
      </span>
    );
  }

  if (status === 'PRE-OPEN') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold bg-yellow-900/70 text-yellow-300 border border-yellow-700/50">
        <span className="inline-block w-2 h-2 rounded-full bg-yellow-400" />
        PRE-OPEN
      </span>
    );
  }

  // CLOSED
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold bg-slate-800/70 text-slate-400 border border-slate-700/50">
      <span className="inline-block w-2 h-2 rounded-full bg-slate-500" />
      CLOSED
    </span>
  );
});

MarketStatusBadge.displayName = 'MarketStatusBadge';
export default MarketStatusBadge;
