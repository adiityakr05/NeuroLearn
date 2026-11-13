import React from 'react';
import { BrainCircuit, TrendingUp, Cpu, RefreshCw, Sparkles, AlertCircle } from 'lucide-react';

export default function LearningElementView({ insights = [] }) {
  return (
    <div className="space-y-6">
      {/* Overview */}
      <div className="p-5 bg-white rounded-3xl border border-slate-200/80 shadow-xs">
        <span className="text-xs font-bold uppercase tracking-wider text-cyan-600">
          Module Role: Retention Model Calibration & Profile Learning
        </span>
        <h2 className="text-lg font-bold text-slate-900 mt-0.5">
          Learning Element Adaptations & Behavioral Profiles
        </h2>
        <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
          The Learning Element improves the agent's internal knowledge base over time. As you complete sessions, it calibrates individual topic decay rates (λ) and personalizes spaced repetition intervals.
        </p>
      </div>

      {/* Model Recalibration Cards */}
      <div className="space-y-4">
        {insights.map((item) => {
          const isImproved = item.status === 'improved';
          const isDecaying = item.status === 'decaying';

          return (
            <div
              key={item.id}
              className="p-5 bg-white rounded-3xl border border-slate-200/80 shadow-xs space-y-3"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-xl bg-cyan-50 text-cyan-700 flex items-center justify-center font-bold text-xs">
                    <Cpu className="w-4 h-4" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{item.module}</h3>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-extrabold px-2.5 py-0.5 rounded-full ${
                      isImproved
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : isDecaying
                        ? 'bg-rose-50 text-rose-700 border border-rose-200'
                        : 'bg-amber-50 text-amber-700 border border-amber-200'
                    }`}
                  >
                    Mastery Delta: {item.masteryChange}
                  </span>
                </div>
              </div>

              {/* Decay Rate Adjustment Details */}
              <div className="p-3 bg-slate-50 rounded-2xl border border-slate-100 text-xs flex items-center justify-between flex-wrap gap-2">
                <span className="text-slate-500 font-semibold">Retention Decay Calibration:</span>
                <code className="text-indigo-600 font-bold bg-white px-2 py-0.5 rounded-md border border-slate-200 text-[11px]">
                  {item.decayRateAdjustment}
                </code>
              </div>

              {/* Behavior Insight */}
              <div className="p-3.5 bg-cyan-50/50 rounded-2xl border border-cyan-100/70 text-xs flex items-start gap-2.5">
                <Sparkles className="w-4 h-4 text-cyan-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-cyan-950">Agent Behavioral Inference:</span>
                  <p className="text-cyan-900 text-[11px] mt-0.5 leading-relaxed">
                    {item.insight}
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
