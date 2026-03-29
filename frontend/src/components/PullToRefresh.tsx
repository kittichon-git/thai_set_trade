// PullToRefresh.tsx — Touch-based pull-to-refresh for mobile
import { useRef, useState, useCallback, type ReactNode } from 'react';

interface Props {
  onRefresh: () => void;
  children: ReactNode;
}

const PULL_THRESHOLD = 60;   // px needed to trigger refresh
const PULL_INDICATOR = 30;   // px before showing indicator

export default function PullToRefresh({ onRefresh, children }: Props) {
  const [pullDistance, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const startYRef = useRef<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    // Only activate when scrolled to top
    if (window.scrollY === 0) {
      startYRef.current = e.touches[0].clientY;
    } else {
      startYRef.current = null;
    }
  }, []);

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (startYRef.current === null || isRefreshing) return;

      const currentY = e.touches[0].clientY;
      const delta = currentY - startYRef.current;

      if (delta > 0 && window.scrollY === 0) {
        // Dampen the pull effect (rubber band)
        const damped = Math.min(delta * 0.5, PULL_THRESHOLD + 20);
        setPullDistance(damped);
      }
    },
    [isRefreshing]
  );

  const handleTouchEnd = useCallback(() => {
    if (startYRef.current === null) return;
    startYRef.current = null;

    if (pullDistance >= PULL_THRESHOLD) {
      setIsRefreshing(true);
      // Give visual feedback before calling refresh
      setTimeout(() => {
        onRefresh();
        setIsRefreshing(false);
        setPullDistance(0);
      }, 500);
    } else {
      setPullDistance(0);
    }
  }, [pullDistance, onRefresh]);

  const showIndicator = pullDistance > PULL_INDICATOR || isRefreshing;
  const arrowRotation = isRefreshing ? 180 : Math.min((pullDistance / PULL_THRESHOLD) * 180, 180);

  return (
    <div
      ref={containerRef}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      className="relative"
    >
      {/* Pull indicator */}
      {showIndicator && (
        <div
          className="absolute top-0 left-0 right-0 flex justify-center items-center py-2 text-slate-400 text-sm z-10 pointer-events-none"
          style={{
            transform: `translateY(${pullDistance - PULL_INDICATOR}px)`,
            opacity: Math.min(pullDistance / PULL_THRESHOLD, 1),
          }}
        >
          <span
            className="inline-block transition-transform ptr-arrow"
            style={{ transform: `rotate(${arrowRotation}deg)` }}
          >
            {isRefreshing ? '↻' : '↓'}
          </span>
          <span className="ml-2 text-xs">
            {isRefreshing
              ? 'กำลังรีเฟรช...'
              : pullDistance >= PULL_THRESHOLD
              ? 'ปล่อยเพื่อรีเฟรช'
              : 'ดึงลงเพื่อรีเฟรช'}
          </span>
        </div>
      )}

      {/* Main content */}
      <div
        style={{
          transform: pullDistance > PULL_INDICATOR ? `translateY(${pullDistance - PULL_INDICATOR}px)` : undefined,
          transition: pullDistance === 0 ? 'transform 0.3s ease-out' : undefined,
        }}
      >
        {children}
      </div>
    </div>
  );
}
