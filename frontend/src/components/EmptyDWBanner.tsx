// EmptyDWBanner.tsx — Warning banner when DW universe is empty
import { memo } from 'react';

const EmptyDWBanner = memo(() => {
  return (
    <div
      className="slide-down mx-3 sm:mx-4 lg:mx-6 mt-3 rounded-xl border border-yellow-700/60 bg-yellow-900/30 px-4 py-3 flex items-start gap-3"
      role="alert"
    >
      <span className="text-yellow-400 text-lg mt-0.5 flex-shrink-0">⚠️</span>
      <div className="text-sm text-yellow-300">
        <span className="font-semibold">ยังไม่มีข้อมูล DW</span>
        {' — '}
        กำลังดึงข้อมูลจาก thaiwarrant.com...
        <div className="text-yellow-500 text-xs mt-1">
          ระบบจะอัปเดตอัตโนมัติ ไม่ต้องรีเฟรช
        </div>
      </div>
    </div>
  );
});

EmptyDWBanner.displayName = 'EmptyDWBanner';
export default EmptyDWBanner;
