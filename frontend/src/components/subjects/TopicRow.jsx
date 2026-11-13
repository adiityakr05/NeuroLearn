import React from 'react';
import {
  CheckCircle2,
  Circle,
  Clock,
  Calendar,
  History,
  Edit2,
  Trash2,
  TrendingUp,
  AlertCircle
} from 'lucide-react';

export default function TopicRow({
  topic,
  onToggleComplete,
  onViewDetails,
  onEdit,
  onDelete,
}) {
  const isDone = topic.completed;

  const difficultyColors = {
    Easy: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    Medium: 'bg-amber-50 text-amber-700 border-amber-200',
    Hard: 'bg-rose-50 text-rose-700 border-rose-200',
  };

  return (
    <div
      className={`p-4 rounded-2xl border transition-all ${
        isDone
          ? 'bg-slate-50/70 border-slate-200/60 opacity-85'
          : 'bg-white border-slate-200/80 hover:border-slate-300 shadow-2xs'
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Left: Completion check & Topic Title */}
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <button
            onClick={() => onToggleComplete(topic.id)}
            className="mt-0.5 text-slate-400 hover:text-indigo-600 transition shrink-0"
            title={isDone ? 'Mark as incomplete' : 'Mark as complete'}
          >
            {isDone ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-500 fill-emerald-50" />
            ) : (
              <Circle className="w-5 h-5" />
            )}
          </button>

          <div className="space-y-1 flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={`text-sm font-bold ${
                  isDone ? 'line-through text-slate-400' : 'text-slate-900'
                }`}
              >
                {topic.name}
              </span>
              <span
                className={`text-[10px] font-extrabold uppercase px-2 py-0.2 rounded-full border ${
                  difficultyColors[topic.difficulty] || 'bg-slate-100 text-slate-600 border-slate-200'
                }`}
              >
                {topic.difficulty}
              </span>
            </div>

            <div className="flex items-center gap-4 text-xs text-slate-500 flex-wrap">
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span>Last Rev: {topic.lastRevised || 'Never'}</span>
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-indigo-500" />
                <span>Next Rev: {topic.nextRevision || 'TBD'}</span>
              </span>
            </div>
          </div>
        </div>

        {/* Center: Mastery indicator */}
        <div className="sm:w-44 flex items-center gap-2.5 sm:px-3">
          <div className="flex-1 space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-slate-400">Mastery</span>
              <strong
                className={
                  topic.mastery >= 75
                    ? 'text-emerald-600 font-bold'
                    : topic.mastery >= 55
                    ? 'text-amber-600 font-bold'
                    : 'text-rose-600 font-bold'
                }
              >
                {topic.mastery}%
              </strong>
            </div>
            <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  topic.mastery >= 75
                    ? 'bg-emerald-500'
                    : topic.mastery >= 55
                    ? 'bg-amber-500'
                    : 'bg-rose-500'
                }`}
                style={{ width: `${topic.mastery}%` }}
              />
            </div>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center justify-end gap-1.5 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100">
          <button
            onClick={() => onViewDetails(topic)}
            title="Inspect Mastery & Revision History"
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-xl transition"
          >
            <History className="w-3.5 h-3.5" />
            <span>History</span>
          </button>
          <button
            onClick={() => onEdit(topic)}
            title="Edit Topic"
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onDelete(topic.id)}
            title="Delete Topic"
            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
