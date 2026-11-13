import React from 'react';
import {
  Sparkles,
  TrendingDown,
  AlertTriangle,
  CalendarClock,
  HelpCircle,
  ArrowRight,
  Info
} from 'lucide-react';

export default function AIRecommendationCard({ recommendation, onAction }) {
  const getBadgeConfig = (type) => {
    switch (type) {
      case 'retention_decay':
        return {
          icon: TrendingDown,
          label: 'Retention Warning',
          bg: 'bg-rose-50 text-rose-700 border-rose-200/80',
          dot: 'bg-rose-500',
        };
      case 'exam_priority':
        return {
          icon: AlertTriangle,
          label: 'Exam Priority',
          bg: 'bg-amber-50 text-amber-700 border-amber-200/80',
          dot: 'bg-amber-500',
        };
      case 'schedule_balance':
        return {
          icon: CalendarClock,
          label: 'Pacing Optimization',
          bg: 'bg-indigo-50 text-indigo-700 border-indigo-200/80',
          dot: 'bg-indigo-500',
        };
      default:
        return {
          icon: HelpCircle,
          label: 'Diagnostic Probe',
          bg: 'bg-emerald-50 text-emerald-700 border-emerald-200/80',
          dot: 'bg-emerald-500',
        };
    }
  };

  const badge = getBadgeConfig(recommendation.type);
  const BadgeIcon = badge.icon;

  return (
    <div className="p-4 sm:p-5 bg-white rounded-2xl border border-slate-200/80 shadow-xs hover:border-indigo-300 transition-all flex flex-col justify-between">
      <div>
        {/* Header Tag and Subject */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${badge.bg}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`}></span>
            <BadgeIcon className="w-3.5 h-3.5" />
            <span>{badge.label}</span>
          </div>
          <span className="text-xs font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
            {recommendation.subject}
          </span>
        </div>

        {/* Action Title */}
        <h4 className="text-sm sm:text-base font-bold text-slate-900 leading-snug mb-2">
          {recommendation.title}
        </h4>

        {/* AI Explainability Box: The 'WHY' */}
        <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-600 space-y-1 mb-4">
          <div className="flex items-center gap-1.5 font-semibold text-slate-700">
            <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
            <span>AI Reasoning: {recommendation.reasonType}</span>
          </div>
          <p className="leading-relaxed text-slate-600">
            {recommendation.reasonDetail}
          </p>
        </div>
      </div>

      {/* Footer Info & Action */}
      <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
        <span className="text-slate-500 font-medium">
          {recommendation.estimatedMinutes > 0 ? `Est. ${recommendation.estimatedMinutes} mins` : 'No study time added'}
        </span>
        <button
          onClick={() => onAction && onAction(recommendation)}
          className="flex items-center gap-1 font-semibold text-indigo-600 hover:text-indigo-700 hover:underline transition-colors"
        >
          <span>{recommendation.actionText}</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
