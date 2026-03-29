// useBreakpoint.ts — Responsive breakpoint detection hook
import { useState, useEffect, useRef } from 'react';

type Breakpoint = 'mobile' | 'tablet' | 'desktop';

function getBreakpoint(width: number): Breakpoint {
  if (width < 768) return 'mobile';
  if (width < 1024) return 'tablet';
  return 'desktop';
}

export function useBreakpoint(): Breakpoint {
  const [bp, setBp] = useState<Breakpoint>('desktop');
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    // Set initial value based on current window width
    setBp(getBreakpoint(window.innerWidth));

    const obs = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width ?? window.innerWidth;
      // Debounce to avoid excessive re-renders during resize
      clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setBp(getBreakpoint(width)), 100);
    });

    // Observe the root element (reflects viewport width)
    obs.observe(document.documentElement);

    return () => {
      obs.disconnect();
      clearTimeout(timerRef.current);
    };
  }, []);

  return bp;
}
