import React from 'react';
import { HelpCircle, Play, Clock, Sparkles, AlertCircle, ArrowRight } from 'lucide-react';

export default function ProblemGeneratorView({ probes = [], onStartActivity }) {
  return (
    <div className="space-y-6">
      {/* Overview */}
      <div className="p-5 bg-white rounded-3xl border border-slate-200/80 shadow-xs">
        <span className="text-xs font-bold uppercase tracking-wider text-amber-600">
          Module Role: Active Exploration & Knowledge Probing
        </span>
        <h2 className="text-lg font-bold text-slate-900 mt-0.5">
          Diagnostic Recall Activities & Exploration Probes
        </h2>
        <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
          The Problem Generator suggests new learning activities and quizzes designed not merely for testing, but to discover areas where the student needs improvement or where the AI lacks confidence in mastery estimations.
        </p>
      </div>

      {/* Probes Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {probes.map((probe) => (
          <div
            key={probe.id}
            className="p-5 bg-white rounded-3xl border border-slate-200/80 shadow-xs hover:border-amber-300 transition-all flex flex-col justify-between space-y-4"
          >
            <div>
              <div className="flex items-center justify-between gap-2 mb-2.5">
                <span className="text-[10px] font-extrabold uppercase px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                  {probe.urgency}
                </span>
                <span className="text-xs font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
                  {probe.subjectCode}
                </span>
              </div>

              <h3 className="text-base font-bold text-slate-900 leading-snug">
                {probe.title}
              </h3>

              <div className="mt-2 flex items-center gap-3 text-xs text-slate-500">
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 text-amber-500" />
                  <span>{probe.durationMinutes} mins</span>
                </span>
                <span>•</span>
                <span>{probe.questionCount} Questions ({probe.format})</span>
              </div>

              {/* Explainability: Why the Agent Generated this Probe */}
              <div className="mt-3.5 p-3.5 bg-amber-50/50 rounded-2xl border border-amber-200/60 text-xs space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-amber-900">
                  <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                  <span>Why This Probe Was Formulated:</span>
                </div>
                <p className="text-amber-800 text-[11px] leading-relaxed">
                  {probe.whyNeeded}
                </p>
              </div>
            </div>

            {/* Launch Action */}
            <div className="pt-2 border-t border-slate-100">
              <button
                onClick={() => onStartActivity(probe)}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold transition shadow-xs"
              >
                <Play className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                <span>Start Diagnostic Activity</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
