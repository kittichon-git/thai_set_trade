// ConnectionBanner.tsx — Sticky WebSocket connection status banner
import { memo } from 'react';

interface Props {
  status: string;
}

const ConnectionBanner = memo(({ status }: Props) => {
  if (status === 'connected') return null;

  if (status === 'connecting') {
    return (
      <div
        className="sticky top-0 z-50 w-full bg-yellow-500/90 text-yellow-950 text-sm font-medium text-center py-2 px-4 backdrop-blur-sm transition-all duration-300"
        role="status"
        aria-live="polite"
      >
        <span className="inline-flex items-center gap-2">
          <span className="live-dot inline-block w-2 h-2 rounded-full bg-yellow-800" />
          กำลังเชื่อมต่อ...
        </span>
      </div>
    );
  }

  // disconnected
  return (
    <div
      className="sticky top-0 z-50 w-full bg-red-600/90 text-white text-sm font-medium text-center py-2 px-4 backdrop-blur-sm transition-all duration-300"
      role="alert"
      aria-live="assertive"
    >
      <span className="inline-flex items-center gap-2">
        <span className="inline-block w-2 h-2 rounded-full bg-red-200" />
        ขาดการเชื่อมต่อ — กำลังเชื่อมต่อใหม่...
      </span>
    </div>
  );
});

ConnectionBanner.displayName = 'ConnectionBanner';
export default ConnectionBanner;
