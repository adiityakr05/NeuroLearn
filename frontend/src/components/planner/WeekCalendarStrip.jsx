import React from 'react';

export default function WeekCalendarStrip({ selectedDate, onSelectDate, weekDates = [] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2.5">
      {weekDates.map((item) => {
        const isSelected = item.date === selectedDate;
        const isToday = item.date === '2026-11-13';

        return (
          <button
            key={item.date}
            onClick={() => onSelectDate(item.date)}
            className={`p-3 rounded-2xl border text-left transition-all ${
              isSelected
                ? 'bg-indigo-600 text-white border-indigo-600 shadow-md shadow-indigo-100 ring-2 ring-indigo-600/20'
                : 'bg-white text-slate-800 border-slate-200/80 hover:border-indigo-300 hover:bg-slate-50'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className={`text-[11px] font-bold uppercase tracking-wider ${isSelected ? 'text-indigo-100' : 'text-slate-400'}`}>
                {item.dayShort}
              </span>
              {isToday && (
                <span
                  className={`text-[9px] font-extrabold uppercase px-1.5 py-0.2 rounded-full ${
                    isSelected ? 'bg-white/20 text-white' : 'bg-indigo-50 text-indigo-600'
                  }`}
                >
                  Today
                </span>
              )}
            </div>

            <div className="flex items-baseline gap-1.5">
              <span className="text-xl font-extrabold">{item.dayNum}</span>
              <span className={`text-xs ${isSelected ? 'text-indigo-200' : 'text-slate-500'}`}>
                {item.monthShort}
              </span>
            </div>

            {/* Task count indicators */}
            <div className="mt-2.5 flex items-center justify-between text-[11px]">
              <span className={`${isSelected ? 'text-indigo-100' : 'text-slate-500'}`}>
                {item.tasksCount} sessions
              </span>
              {item.hasOverdue && (
                <span className="w-2 h-2 rounded-full bg-rose-400 ring-2 ring-white"></span>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
