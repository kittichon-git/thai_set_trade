// LoadingState.tsx — Full-page skeleton loading state
import { memo } from 'react';

interface Props {
  message?: string;
}

const LoadingState = memo(({ message = 'กำลังโหลดข้อมูลตลาด...' }: Props) => {
  return (
    <div className="fade-in min-h-[60vh] flex flex-col gap-4 pt-4">
      {/* Header skeleton */}
      <div className="animate-pulse flex gap-3 items-center mb-2">
        <div className="h-4 bg-slate-700 rounded w-40" />
        <div className="h-4 bg-slate-800 rounded w-24" />
      </div>

      {/* Row skeletons */}
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="animate-pulse bg-slate-800/60 rounded-xl p-4 flex flex-col gap-3 border border-slate-700/40"
        >
          <div className="flex justify-between items-center">
            <div className="flex gap-3 items-center">
              <div className="h-5 bg-slate-700 rounded w-6" />
              <div className="h-5 bg-slate-600 rounded w-20" />
            </div>
            <div className="h-6 bg-slate-700 rounded-full w-16" />
          </div>
          <div className="flex gap-4">
            <div className="h-4 bg-slate-700 rounded w-16" />
            <div className="h-4 bg-slate-700 rounded w-20" />
            <div className="h-4 bg-slate-700 rounded w-28" />
          </div>
        </div>
      ))}

      {/* Loading message */}
      <div className="text-center text-slate-500 text-sm mt-4 animate-pulse">
        {message}
      </div>
    </div>
  );
});

LoadingState.displayName = 'LoadingState';
export default LoadingState;
