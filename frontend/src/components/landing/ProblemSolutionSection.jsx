import React from 'react';
import { XCircle, CheckCircle2, AlertOctagon, Sparkles } from 'lucide-react';

export default function ProblemSolutionSection() {
  return (
    <section id="problem-solution" className="py-20 bg-slate-50 border-y border-slate-200/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
            The Paradigm Shift
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            Traditional Timetables Fail. <br />
            Here Is Why Adaptive Agents Win.
          </h2>
          <p className="text-sm text-slate-500 leading-relaxed">
            Human memory does not decay on a rigid linear calendar. Studying harder isn't the solution—studying at the scientifically optimal moment is.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto">
          {/* Traditional Study Planners (The Flaw) */}
          <div className="p-8 bg-white rounded-3xl border border-rose-100 shadow-xs space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center">
                <XCircle className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Traditional Fixed Timetables</h3>
                <span className="text-xs font-semibold text-rose-600">Static, Rigid & Inefficient</span>
              </div>
            </div>

            <ul className="space-y-4 text-xs sm:text-sm text-slate-600">
              <li className="flex items-start gap-3">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-2 shrink-0"></span>
                <span><strong>Ignored Forgetting Curves:</strong> Assumes a topic studied once remains fully retained forever without systematic review.</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-2 shrink-0"></span>
                <span><strong>Zero Cognitive Feedback:</strong> Never adapts when you score poorly on a mock test or encounter a hard topic.</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-2 shrink-0"></span>
                <span><strong>Fragile When Disrupted:</strong> Missing one day causes the entire schedule to collapse into panic and cramming.</span>
              </li>
            </ul>
          </div>

          {/* NeuroLearn Adaptive System (The Solution) */}
          <div className="p-8 bg-white rounded-3xl border border-indigo-200 ring-2 ring-indigo-50 shadow-md space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <Sparkles className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">NeuroLearn Adaptive Agent</h3>
                <span className="text-xs font-semibold text-indigo-600">Dynamic, Scientific & Resilient</span>
              </div>
            </div>

            <ul className="space-y-4 text-xs sm:text-sm text-slate-600">
              <li className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                <span><strong>Spaced Repetition Engine:</strong> Calculates individual memory decay trajectories and schedules active recall right before forgetting occurs.</span>
              </li>
              <li className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                <span><strong>Continuous Critic Audit:</strong> If a quiz score drops, the agent automatically prioritizes prerequisite concepts and adjusts exam prep.</span>
              </li>
              <li className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                <span><strong>Cognitive Load Balancing:</strong> Rescheduling a session triggers mathematical re-balancing to ensure safe retention decay.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
