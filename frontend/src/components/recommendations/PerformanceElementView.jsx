import React, { useState } from 'react';
import {
  Sparkles,
  Clock,
  Calendar,
  AlertTriangle,
  TrendingDown,
  Check,
  X,
  ChevronRight,
  Info
} from 'lucide-react';

export default function PerformanceElementView({
  recommendations = [],
  onAccept,
  onDismiss,
  onInspectReason,
}) {
  const [filterType, setFilterType] = useState('all');

  const filtered =
    filterType === 'all'
      ? recommendations
      : recommendations.filter((r) => r.type === filterType);

  return (
    <div className="space-y-6">
      {/* Overview Card */}
      <div className="p-5 bg-white rounded-3xl border border-slate-200/80 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
              Module Role: Agent Actuator
            </span>
          </div>
          <h2 className="text-lg font-bold text-slate-900 mt-0.5">
            Active Study Recommendations Generated for Aditya
          </h2>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
            The Performance Element synthesizes your daily study agenda by balancing memory retention decay, upcoming examination weights, and available study hours.
          </p>
        </div>

        {/* Filter pills */}
        <div className="flex items-center gap-1.5 flex-wrap text-xs self-start md:self-auto">
          {['all', 'retention_decay', 'exam_priority', 'pacing_optimization'].map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-3 py-1.5 rounded-xl font-bold transition capitalize ${
                filterType === type
                  ? 'bg-slate-900 text-white shadow-2xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {type === 'all' ? 'All Triggers' : type.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Recommendations Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered.map((rec) => {
          const isUrgent = rec.priority === 'urgent' || rec.priority === 'high';

          return (
            <div
              key={rec.id}
              className="p-5 bg-white rounded-3xl border border-slate-200/80 shadow-xs hover:border-indigo-300 transition-all flex flex-col justify-between space-y-4"
            >
              <div>
                {/* Header Tag */}
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span
                    className={`text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full border ${
                      isUrgent
                        ? 'bg-rose-50 text-rose-700 border-rose-200'
                        : 'bg-indigo-50 text-indigo-700 border-indigo-200'
                    }`}
                  >
                    {rec.priority} Priority
                  </span>
                  <span className="text-xs font-bold text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded-md">
                    {rec.subject} ({rec.subjectCode})
                  </span>
                </div>

                {/* Title */}
                <h3 className="text-base font-bold text-slate-900 leading-snug">
                  {rec.title}
                </h3>

                {/* Key Attributes */}
                <div className="mt-2.5 flex items-center gap-4 text-xs text-slate-500 flex-wrap">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-indigo-500" />
                    <span>Est: {rec.durationMinutes > 0 ? `${rec.durationMinutes} mins` : 'Re-balance'}</span>
                  </span>
                  <span>Urgency: <strong className="text-slate-800">{rec.examUrgency}</strong></span>
                  {rec.retentionScore && (
                    <span>Retention: <strong className="text-rose-600">{rec.retentionScore}%</strong></span>
                  )}
                </div>

                {/* Explainable AI Reasoning Box: The Crucial "Why" */}
                <div className="mt-3.5 p-3.5 bg-slate-50 rounded-2xl border border-slate-200/70 text-xs space-y-1">
                  <div className="flex items-center gap-1.5 font-bold text-slate-800">
                    <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                    <span>Explainable AI Reason: {rec.reasonType}</span>
                  </div>
                  <p className="text-slate-600 leading-relaxed text-[11px]">
                    {rec.reasonDetail}
                  </p>
                  <p className="text-[10px] text-indigo-700 font-semibold pt-1">
                    Suggested Slot: {rec.suggestedSlot}
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
                <button
                  onClick={() => onDismiss(rec.id)}
                  className="flex items-center gap-1 text-slate-400 hover:text-slate-700 font-semibold transition"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Dismiss</span>
                </button>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onInspectReason(rec)}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-bold transition"
                  >
                    Why this topic?
                  </button>
                  <button
                    onClick={() => onAccept(rec.id)}
                    className="flex items-center gap-1 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold transition shadow-2xs"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Accept & Plan</span>
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
