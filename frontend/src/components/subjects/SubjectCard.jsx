import React from 'react';
import { BookOpen, MoreVertical, Edit2, Trash2, CheckCircle2 } from 'lucide-react';

export default function SubjectCard({
  subject,
  isSelected,
  onSelect,
  onEdit,
  onDelete,
}) {
  const totalTopics = subject.topics.length;
  const completedTopics = subject.topics.filter((t) => t.completed).length;
  const progressPercent = totalTopics > 0 ? Math.round((completedTopics / totalTopics) * 100) : 0;
  
  // Calculate average mastery
  const avgMastery =
    totalTopics > 0
      ? Math.round(subject.topics.reduce((sum, t) => sum + (t.mastery || 0), 0) / totalTopics)
      : 0;

  return (
    <div
      onClick={onSelect}
      className={`relative p-5 rounded-3xl border text-left cursor-pointer transition-all duration-200 ${
        isSelected
          ? 'bg-white border-indigo-600 ring-2 ring-indigo-500/20 shadow-md'
          : 'bg-white border-slate-200/80 hover:border-slate-300 shadow-xs hover:shadow-sm'
      }`}
    >
      {/* Top Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5">
          <div
            className="w-10 h-10 rounded-2xl flex items-center justify-center text-white font-bold text-sm shadow-xs"
            style={{ backgroundColor: subject.color || '#6366F1' }}
          >
            {subject.code ? subject.code.slice(0, 2) : 'SB'}
          </div>
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              {subject.code}
            </span>
            <h3 className="text-base font-bold text-slate-900 leading-snug line-clamp-1">
              {subject.name}
            </h3>
          </div>
        </div>

        {/* Action icons */}
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => onEdit(subject)}
            title="Edit Subject"
            className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-slate-100 rounded-lg transition"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onDelete(subject.id)}
            title="Delete Subject"
            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <p className="text-xs text-slate-500 line-clamp-2 mb-4 leading-relaxed">
        {subject.description || 'No description provided.'}
      </p>

      {/* Progress metrics */}
      <div className="space-y-2 pt-2 border-t border-slate-100">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500 font-medium">Completion Progress</span>
          <span className="font-bold text-slate-900">
            {completedTopics}/{totalTopics} Topics ({progressPercent}%)
          </span>
        </div>
        <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-300"
            style={{
              width: `${progressPercent}%`,
              backgroundColor: subject.color || '#6366F1',
            }}
          />
        </div>

        <div className="flex items-center justify-between text-xs pt-1 text-slate-500">
          <span>Avg. Mastery</span>
          <strong className={avgMastery >= 75 ? 'text-emerald-600' : 'text-amber-600'}>
            {avgMastery}%
          </strong>
        </div>
      </div>
    </div>
  );
}
