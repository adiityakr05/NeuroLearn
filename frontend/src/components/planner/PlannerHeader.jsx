import React from 'react';
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon, Sparkles } from 'lucide-react';
import { formatLocalDateTitle } from '../../utils/dateUtils';

export default function PlannerHeader({
  currentDate,
  viewMode,
  onViewModeChange,
  onPrev,
  onNext,
  onToday,
  totalSessions,
  completedSessions,
  totalHours,
}) {
  const displayTitle = formatLocalDateTitle(currentDate);

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between pb-6 border-b border-slate-200/80">
      {/* Title & Date Navigation */}
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Adaptive Study Planner
          </h1>
          <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100">
            <Sparkles className="w-3.5 h-3.5" />
            Spaced Repetition Calibrated
          </span>
        </div>

        {/* Date Selector Strip */}
        <div className="flex items-center gap-2.5 mt-2 flex-wrap">
          <div className="flex items-center bg-white border border-slate-200 rounded-xl p-1 shadow-2xs">
            <button
              onClick={onPrev}
              title="Previous day"
              className="p-1.5 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <div className="px-3 py-1 flex items-center gap-1.5 text-xs sm:text-sm font-semibold text-slate-800">
              <CalendarIcon className="w-4 h-4 text-indigo-600" />
              <span>{displayTitle}</span>
            </div>
            <button
              onClick={onNext}
              title="Next day"
              className="p-1.5 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <button
            onClick={onToday}
            className="px-3 py-1.5 bg-white border border-slate-200 text-xs font-bold text-slate-700 rounded-xl hover:bg-slate-50 transition shadow-2xs"
          >
            Today
          </button>
        </div>
      </div>

      {/* View Switcher & Day Metrics */}
      <div className="flex items-center gap-3 self-start lg:self-auto flex-wrap">
        {/* Progress Pill */}
        <div className="flex items-center gap-2 px-3 py-2 bg-white rounded-xl border border-slate-200 text-xs font-medium text-slate-600 shadow-2xs">
          <span>Target: <strong className="text-slate-900">{totalHours}h</strong></span>
          <span className="text-slate-300">•</span>
          <span>Sessions: <strong className="text-slate-900">{completedSessions}/{totalSessions}</strong></span>
        </div>

        {/* Day / Week View Mode Switcher */}
        <div className="flex items-center p-1 bg-slate-200/70 rounded-xl">
          <button
            onClick={() => onViewModeChange('day')}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg transition ${
              viewMode === 'day'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Day View
          </button>
          <button
            onClick={() => onViewModeChange('week')}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg transition ${
              viewMode === 'week'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            7-Day Week
          </button>
        </div>
      </div>
    </div>
  );
}
