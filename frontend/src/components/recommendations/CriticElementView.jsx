import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, ShieldAlert, Sparkles, History } from 'lucide-react';

export default function CriticElementView({ evaluations = [] }) {
  const getStatusBadge = (status) => {
    switch (status) {
      case 'success':
        return {
          icon: CheckCircle2,
          bg: 'bg-emerald-50 text-emerald-700 border-emerald-200',
          dot: 'bg-emerald-500',
        };
      case 'warning':
        return {
          icon: AlertTriangle,
          bg: 'bg-amber-50 text-amber-700 border-amber-200',
          dot: 'bg-amber-500',
        };
      default:
        return {
          icon: XCircle,
          bg: 'bg-rose-50 text-rose-700 border-rose-200',
          dot: 'bg-rose-500',
        };
    }
  };

  return (
    <div className="space-y-6">
      {/* Header explanation */}
      <div className="p-5 bg-white rounded-3xl border border-slate-200/80 shadow-xs">
        <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
          Module Role: System Evaluator & Feedback Agent
        </span>
        <h2 className="text-lg font-bold text-slate-900 mt-0.5">
          Critic Evaluation Audit & Recommendation Effectiveness
        </h2>
        <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
          The Critic continuously verifies whether previous AI recommendations were followed by the student, compares expected vs. actual test outcomes, and sends feedback to the Learning Element.
        </p>
      </div>

      {/* Audit Log Cards */}
      <div className="space-y-4">
        {evaluations.map((item) => {
          const badge = getStatusBadge(item.status);
          const Icon = badge.icon;

          return (
            <div
              key={item.id}
              className="p-5 bg-white rounded-3xl border border-slate-200/80 shadow-xs space-y-3"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <span className={`p-1 rounded-lg border ${badge.bg}`}>
                    <Icon className="w-4 h-4" />
                  </span>
                  <span className="text-sm font-bold text-slate-900">
                    {item.recommendationGiven}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-400">{item.date}</span>
                  <span className={`text-xs font-extrabold px-2.5 py-0.5 rounded-full border ${badge.bg}`}>
                    {item.effectivenessRating}
                  </span>
                </div>
              </div>

              {/* Expected vs Actual Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="text-slate-400 font-bold uppercase text-[10px] block mb-1">
                    Student Action & Expected Target
                  </span>
                  <p className="font-semibold text-slate-800">{item.studentAction}</p>
                  <p className="text-slate-500 text-[11px] mt-0.5">Benchmark: {item.expectedOutcome}</p>
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="text-slate-400 font-bold uppercase text-[10px] block mb-1">
                    Actual Outcome Measured
                  </span>
                  <p className="font-bold text-slate-900">{item.actualOutcome}</p>
                  <p className="text-slate-500 text-[11px] mt-0.5">Recorded by Diagnostic Test Evaluator</p>
                </div>
              </div>

              {/* Critic AI Feedback Note */}
              <div className="p-3.5 bg-indigo-50/60 rounded-2xl border border-indigo-100/70 text-xs flex items-start gap-2.5">
                <Sparkles className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-indigo-950">Critic Synthesis & Feedback:</span>
                  <p className="text-indigo-800 text-[11px] mt-0.5 leading-relaxed">
                    {item.feedbackNote}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
