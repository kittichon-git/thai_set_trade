// VolumeRatioBadge.tsx — Volume ratio strength pill badge
import { memo } from 'react';

interface Props {
  ratio: number;
  strength: '2x+' | '3x+' | '5x+';
}

const VolumeRatioBadge = memo(({ ratio, strength }: Props) => {
  const baseClasses =
    'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold num touch-target justify-center select-none';

  if (strength === '5x+') {
    return (
      <span
        className={`${baseClasses} bg-red-900/80 text-red-200 border border-red-700/60`}
        title="Volume 5x+ above average"
      >
        <span className="live-dot inline-block w-2 h-2 rounded-full bg-red-400" />
        {ratio.toFixed(1)}x
      </span>
    );
  }

  if (strength === '3x+') {
    return (
      <span
        className={`${baseClasses} bg-orange-900/80 text-orange-200 border border-orange-700/60`}
        title="Volume 3x+ above average"
      >
        <span className="inline-block w-2 h-2 rounded-full bg-orange-400" />
        {ratio.toFixed(1)}x
      </span>
    );
  }

  // strength === '2x+'
  return (
    <span
      className={`${baseClasses} bg-yellow-900/80 text-yellow-200 border border-yellow-700/60`}
      title="Volume 2x+ above average"
    >
      <span className="inline-block w-2 h-2 rounded-full bg-yellow-400" />
      {ratio.toFixed(1)}x
    </span>
  );
});

VolumeRatioBadge.displayName = 'VolumeRatioBadge';
export default VolumeRatioBadge;
