import React from 'react';
import { X, History, TrendingUp, Sparkles, Calendar, CheckCircle2 } from 'lucide-react';

export default function TopicDetailsModal({ topic, isOpen, onClose }) {
  if (!isOpen || !topic) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
      <div className="bg-white rounded-3xl max-w-lg w-full border border-slate-200 shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="p-5 sm:p-6 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <History className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Topic Performance & History</h3>
              <p className="text-xs text-slate-500">Historical recall logs used by the Learning Element</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 sm:p-6 space-y-5 max-h-[75vh] overflow-y-auto">
          {/* Main Topic Info Card */}
          <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/80">
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
                Difficulty: {topic.difficulty}
              </span>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                  topic.completed ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                }`}
              >
                {topic.completed ? 'Completed' : 'In Progress'}
              </span>
            </div>
            <h4 className="text-base font-extrabold text-slate-900">{topic.name}</h4>

            {/* Estimated Mastery Progress */}
            <div className="mt-3 space-y-1">
              <div className="flex justify-between text-xs text-slate-600">
                <span>Estimated Topic Mastery</span>
                <strong className="text-slate-900">{topic.mastery}%</strong>
              </div>
              <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-indigo-600 rounded-full"
                  style={{ width: `${topic.mastery}%` }}
                />
              </div>
            </div>
          </div>

          {/* AI Learning Element Note */}
          <div className="p-3.5 bg-indigo-50/70 rounded-2xl border border-indigo-100/80 text-xs text-indigo-900 flex items-start gap-2.5">
            <Sparkles className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Learning Model Calibration:</p>
              <p className="mt-0.5 leading-relaxed text-indigo-800">
                Next optimal recall window is scheduled on <strong className="text-indigo-950">{topic.nextRevision || 'TBD'}</strong> to prevent forgetting decay below the target 70% threshold.
              </p>
            </div>
          </div>

          {/* Revision History Timeline */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              Spaced Repetition Log ({topic.revisionHistory?.length || 0} Sessions)
            </h4>

            {topic.revisionHistory && topic.revisionHistory.length > 0 ? (
              <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                {topic.revisionHistory.map((rev, idx) => (
                  <div key={idx} className="relative">
                    {/* Timeline bullet */}
                    <div className="absolute -left-6 top-1 w-4 h-4 rounded-full bg-white border-2 border-indigo-600 flex items-center justify-center">
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-600"></div>
                    </div>

                    <div className="p-3 bg-white rounded-xl border border-slate-200/80 shadow-2xs">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-bold text-slate-900">{rev.date}</span>
                        <span className="font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md">
                          Score: {rev.score}%
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">{rev.note}</p>
                      {rev.intervalDays > 0 && (
                        <span className="inline-block text-[10px] text-slate-400 font-medium mt-1">
                          Gap: {rev.intervalDays} days from previous session
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No historical revisions recorded yet.</p>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-100 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-100 text-slate-700 text-xs font-bold rounded-xl hover:bg-slate-200 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
