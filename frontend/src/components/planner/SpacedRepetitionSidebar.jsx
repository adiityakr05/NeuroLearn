import React from 'react';
import { Repeat, AlertCircle, ArrowUpRight, CheckCircle2 } from 'lucide-react';

export default function SpacedRepetitionSidebar({ items = [] }) {
  const getUrgencyBadge = (urgency) => {
    switch (urgency) {
      case 'critical':
        return {
          bg: 'bg-rose-50 text-rose-700 border-rose-200',
          dot: 'bg-rose-500',
          label: 'Critical Recall',
        };
      case 'warning':
        return {
          bg: 'bg-amber-50 text-amber-700 border-amber-200',
          dot: 'bg-amber-500',
          label: 'Review Due',
        };
      case 'optimal':
        return {
          bg: 'bg-indigo-50 text-indigo-700 border-indigo-200',
          dot: 'bg-indigo-500',
          label: 'Optimal Gap',
        };
      default:
        return {
          bg: 'bg-emerald-50 text-emerald-700 border-emerald-200',
          dot: 'bg-emerald-500',
          label: 'Retained',
        };
    }
  };

  return (
    <div className="bg-white rounded-3xl border border-slate-200/80 shadow-xs p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-1.5">
            <Repeat className="w-4 h-4 text-indigo-600" />
            <h3 className="text-base font-bold text-slate-900">Spaced Repetition Queue</h3>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">Based on Ebbinghaus forgetting curves</p>
        </div>
        <span className="text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-100 px-2 py-0.5 rounded-full">
          {items.length} Active
        </span>
      </div>

      {/* Review cards */}
      <div className="space-y-3">
        {items.map((item) => {
          const badge = getUrgencyBadge(item.urgency);

          return (
            <div
              key={item.id}
              className="p-3.5 rounded-2xl border border-slate-100 bg-slate-50/60 hover:bg-slate-50 transition"
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="text-[11px] font-semibold text-slate-500">{item.subject}</span>
                <span
                  className={`flex items-center gap-1 text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full border ${badge.bg}`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`}></span>
                  <span>{badge.label}</span>
                </span>
              </div>

              <h4 className="text-xs sm:text-sm font-bold text-slate-900 leading-snug">
                {item.topic}
              </h4>

              {/* Retention bar */}
              <div className="mt-2.5 space-y-1">
                <div className="flex justify-between text-[11px] text-slate-500">
                  <span>Current Retention</span>
                  <strong className={item.estimatedRetention < 65 ? 'text-rose-600' : 'text-slate-900'}>
                    {item.estimatedRetention}%
                  </strong>
                </div>
                <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      item.estimatedRetention < 65 ? 'bg-rose-500' : 'bg-indigo-600'
                    }`}
                    style={{ width: `${item.estimatedRetention}%` }}
                  />
                </div>
              </div>

              {/* Intervals meta */}
              <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-slate-200/50 text-[11px] text-slate-500">
                <span>{item.repetitionStage}</span>
                <span className="font-semibold text-slate-700">Exam: {item.examWeight}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
