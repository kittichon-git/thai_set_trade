// PriceChange.tsx — Price change percentage display with flash animation
import { memo, useRef, useEffect, useState } from 'react';
import { formatChangePct } from '../utils/format';

interface Props {
  value: number;
  prevValue?: number;
}

const PriceChange = memo(({ value, prevValue }: Props) => {
  const [flashClass, setFlashClass] = useState('');
  const prevRef = useRef<number | undefined>(prevValue);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    const prev = prevRef.current;
    prevRef.current = value;

    // Flash on value change when prevValue is provided
    if (prev !== undefined && prev !== value) {
      const cls = value > prev ? 'flash-up' : 'flash-down';
      setFlashClass(cls);
      clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setFlashClass(''), 850);
    }

    return () => clearTimeout(timerRef.current);
  }, [value]);

  if (value > 0) {
    return (
      <span
        className={`num text-emerald-400 font-medium ${flashClass}`}
        aria-label={`Up ${value.toFixed(2)} percent`}
      >
        ▲ {formatChangePct(value)}
      </span>
    );
  }

  if (value < 0) {
    return (
      <span
        className={`num text-red-400 font-medium ${flashClass}`}
        aria-label={`Down ${Math.abs(value).toFixed(2)} percent`}
      >
        ▼ {formatChangePct(value)}
      </span>
    );
  }

  return (
    <span className="num text-slate-400 font-medium" aria-label="No change">
      — 0.00%
    </span>
  );
});

PriceChange.displayName = 'PriceChange';
export default PriceChange;
