import React from 'react';
import {
  Clock,
  CheckCircle2,
  Circle,
  CalendarClock,
  Sparkles,
  AlertCircle,
  ArrowRight,
  RefreshCw,
  Repeat
} from 'lucide-react';

export default function DailySessionCard({ session, onToggleStatus, onOpenReschedule }) {
  const isDone = session.status === 'completed';
  const isInProgress = session.status === 'in_progress';

  return (
    <div
      className={`p-5 rounded-2xl border transition-all ${
        isDone
          ? 'bg-slate-50/80 border-slate-200/60 opacity-85'
          : isInProgress
          ? 'bg-white border-indigo-300 ring-2 ring-indigo-50 shadow-sm'
          : 'bg-white border-slate-200/80 shadow-xs hover:border-slate-300'
      }`}
    >
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        {/* Left Section: Checkbox & Topic Details */}
        <div className="flex items-start gap-3.5 flex-1 min-w-0">
          <button
            onClick={() => onToggleStatus(session.id, isDone ? 'pending' : 'completed')}
            className="mt-0.5 text-slate-400 hover:text-indigo-600 transition-colors focus:outline-none shrink-0"
            title={isDone ? 'Mark as incomplete' : 'Mark as completed'}
          >
            {isDone ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-500 fill-emerald-50" />
            ) : (
              <Circle className="w-5 h-5" />
            )}
          </button>

          <div className="space-y-2 flex-1 min-w-0">
            {/* Badges strip */}
            <div className="flex items-center gap-2 flex-wrap text-xs">
              <span className="font-bold text-slate-800 bg-slate-100 px-2.5 py-0.5 rounded-md">
                {session.subject}
              </span>

              {session.repetitionCycle && (
                <span className="flex items-center gap-1 font-semibold text-indigo-700 bg-indigo-50 border border-indigo-100 px-2 py-0.5 rounded-md">
                  <Repeat className="w-3 h-3" />
                  <span>{session.repetitionCycle}</span>
                </span>
              )}

              {session.isOverdue && !isDone && (
                <span className="flex items-center gap-1 font-bold text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-md">
                  <AlertCircle className="w-3 h-3" />
                  <span>Revision Overdue</span>
                </span>
              )}

              <span
                className={`uppercase text-[10px] font-extrabold tracking-wider px-2 py-0.5 rounded-full ${
                  session.priority === 'high'
                    ? 'bg-rose-50 text-rose-700 border border-rose-100'
                    : session.priority === 'medium'
                    ? 'bg-amber-50 text-amber-700 border border-amber-100'
                    : 'bg-slate-100 text-slate-600'
                }`}
              >
                {session.priority} Priority
              </span>
            </div>

            {/* Topic Title */}
            <h3
              className={`text-base font-bold ${
                isDone ? 'line-through text-slate-500' : 'text-slate-900'
              }`}
            >
              {session.topic}
            </h3>

            {/* Meta attributes */}
            <div className="flex items-center gap-4 text-xs text-slate-500 flex-wrap">
              <span className="flex items-center gap-1 font-medium text-slate-700">
                <Clock className="w-3.5 h-3.5 text-indigo-500" />
                {session.timeSlot} ({session.durationMinutes} mins)
              </span>

              <span className="flex items-center gap-1">
                <span>Memory Retention:</span>
                <strong
                  className={
                    session.retentionScore < 65 ? 'text-rose-600 font-bold' : 'text-emerald-600 font-bold'
                  }
                >
                  {session.retentionScore}%
                </strong>
              </span>
            </div>

            {/* Explainable AI Reasoning Pill */}
            <div className="p-3 bg-slate-50/90 rounded-xl border border-slate-200/70 text-xs text-slate-600 space-y-1">
              <div className="flex items-center gap-1.5 font-bold text-indigo-900">
                <Sparkles className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                <span>AI Scheduling Logic:</span>
              </div>
              <p className="leading-relaxed text-slate-600">
                {session.aiReason}
              </p>
            </div>
          </div>
        </div>

        {/* Right Section: Action Controls */}
        <div className="flex items-center md:flex-col justify-end gap-2 shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100">
          <button
            onClick={() => onOpenReschedule(session)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 hover:text-slate-900 rounded-xl transition"
          >
            <CalendarClock className="w-3.5 h-3.5 text-slate-500" />
            <span>Reschedule</span>
          </button>

          <button
            onClick={() => onToggleStatus(session.id, isDone ? 'pending' : 'completed')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl transition ${
              isDone
                ? 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-xs'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{isDone ? 'Undo Done' : 'Complete'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
