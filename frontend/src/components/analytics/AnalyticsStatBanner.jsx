import React from 'react';
import {
  BrainCircuit,
  Award,
  CalendarCheck2,
  ClockAlert,
  TrendingUp,
  Sparkles
} from 'lucide-react';

export default function AnalyticsStatBanner({ summary }) {
  if (!summary) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Predicted Retention */}
      <div className="p-5 bg-white rounded-3xl border border-slate-200/80 shadow-xs">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Predicted Memory Retention
          </span>
          <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <BrainCircuit className="w-5 h-5" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {summary.predictedOverallRetention}%
          </span>
          <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-md">
            +4.1% MoM
          </span>
        </div>
        <p className="text-[11px] text-slate-500 mt-1">
          ML model estimate across all active modules
        </p>
      </div>

      {/* Quiz Average */}
      <div className="p-5 bg-white rounded-3xl border border-slate-200/80 shadow-xs">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Average Quiz Accuracy
          </span>
          <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <Award className="w-5 h-5" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {summary.averageQuizAccuracy}%
          </span>
          <span className="text-xs font-semibold text-slate-500">
            (Actual recall avg: {summary.actualRecallAverage}%)
          </span>
        </div>
        <p className="text-[11px] text-slate-500 mt-1">
          Based on 7 completed recall checks
        </p>
      </div>

      {/* Revision Compliance */}
      <div className="p-5 bg-white rounded-3xl border border-slate-200/80 shadow-xs">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Revision Adherence
          </span>
          <div className="w-9 h-9 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center">
            <CalendarCheck2 className="w-5 h-5" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {summary.revisionComplianceRate}%
          </span>
          <span className="text-xs font-semibold text-cyan-700 bg-cyan-50 px-1.5 py-0.5 rounded-md">
            Avg gap {summary.averageIntervalDays}d
          </span>
        </div>
        <p className="text-[11px] text-slate-500 mt-1">
          Sessions completed on AI scheduled dates
        </p>
      </div>

      {/* Overdue Revisions */}
      <div className="p-5 bg-white rounded-3xl border border-slate-200/80 shadow-xs">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Overdue Memory Reviews
          </span>
          <div className="w-9 h-9 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
            <ClockAlert className="w-5 h-5" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-rose-600 tracking-tight">
            {summary.overdueRevisionsCount}
          </span>
          <span className="text-xs font-semibold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded-md">
            Urgent Recall
          </span>
        </div>
        <p className="text-[11px] text-slate-500 mt-1">
          Predicted decay exceeds optimal review threshold
        </p>
      </div>
    </div>
  );
}
