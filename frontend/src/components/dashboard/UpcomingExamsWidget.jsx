import React from 'react';
import { Calendar, AlertCircle } from 'lucide-react';

export default function UpcomingExamsWidget({ exams = [] }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-bold text-slate-900">Upcoming Examinations</h3>
          <p className="text-xs text-slate-500">Target vs current estimated topic mastery</p>
        </div>
      </div>

      <div className="space-y-3.5">
        {exams.map((exam) => {
          const isCritical = exam.status === 'critical';
          const masteryDiff = exam.targetMastery - exam.currentMastery;

          return (
            <div key={exam.id} className="p-3.5 rounded-xl border border-slate-100 bg-slate-50/60">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h4 className="text-sm font-bold text-slate-900">{exam.subject}</h4>
                  <span className="text-[11px] font-medium text-slate-500">{exam.code}</span>
                </div>
                <div className="text-right">
                  <span
                    className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md ${
                      isCritical
                        ? 'bg-rose-50 text-rose-600 border border-rose-100'
                        : 'bg-emerald-50 text-emerald-600 border border-emerald-100'
                    }`}
                  >
                    <Calendar className="w-3 h-3" />
                    <span>In {exam.daysLeft} days</span>
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="space-y-1 mt-3">
                <div className="flex justify-between text-xs text-slate-600">
                  <span>Current Mastery: <strong className="text-slate-900">{exam.currentMastery}%</strong></span>
                  <span className="text-slate-500">Target: {exam.targetMastery}%</span>
                </div>
                <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      isCritical ? 'bg-rose-500' : 'bg-indigo-600'
                    }`}
                    style={{ width: `${exam.currentMastery}%` }}
                  />
                </div>
              </div>

              {isCritical && (
                <div className="mt-2.5 flex items-center gap-1.5 text-[11px] text-rose-600 font-medium">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>Gap of {masteryDiff}% to reach target. Priority increased in planner.</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
