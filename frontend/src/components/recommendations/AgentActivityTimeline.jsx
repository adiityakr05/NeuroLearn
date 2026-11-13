import React, { useState } from 'react';
import { ArrowRight, CheckCircle2, RotateCw, Brain, Sparkles, AlertCircle } from 'lucide-react';

export default function AgentActivityTimeline({ timeline = [] }) {
  const [activeStep, setActiveStep] = useState(null);
  const [simulating, setSimulating] = useState(false);
  const [currentTimeline, setCurrentTimeline] = useState(timeline);

  const handleSimulateCycle = () => {
    setSimulating(true);
    setTimeout(() => {
      setSimulating(false);
      alert('Cycle Simulation Completed: Critic recalculated performance, Learning Element updated weights, and Performance Element re-balanced today’s schedule.');
    }, 600);
  };

  const getElementBadgeColor = (color) => {
    switch (color) {
      case 'emerald':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'indigo':
        return 'bg-indigo-50 text-indigo-700 border-indigo-200';
      case 'cyan':
        return 'bg-cyan-50 text-cyan-700 border-cyan-200';
      default:
        return 'bg-amber-50 text-amber-700 border-amber-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Overview and Simulator Trigger */}
      <div className="p-5 bg-white rounded-3xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
            Cognitive Loop Trace (End-to-End Execution Flow)
          </span>
          <h2 className="text-lg font-bold text-slate-900 mt-0.5">
            The 5-Step Continuous Adaptive Learning Loop
          </h2>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
            Trace how a single quiz submission travels through the Critic, modifies Learning parameters, updates the Performance schedule, and prompts the Problem Generator.
          </p>
        </div>

        <button
          onClick={handleSimulateCycle}
          disabled={simulating}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition shadow-xs self-start sm:self-auto shrink-0"
        >
          <RotateCw className={`w-3.5 h-3.5 ${simulating ? 'animate-spin' : ''}`} />
          <span>{simulating ? 'Simulating Cycle...' : 'Simulate Feedback Cycle'}</span>
        </button>
      </div>

      {/* Step by step vertical trace */}
      <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 sm:before:left-4 before:top-4 before:bottom-4 before:w-0.5 before:bg-indigo-100">
        {currentTimeline.map((stepItem) => {
          const badgeClass = getElementBadgeColor(stepItem.badgeColor);

          return (
            <div key={stepItem.step} className="relative">
              {/* Step indicator node */}
              <div className="absolute -left-6 sm:-left-8 top-1 w-6 h-6 rounded-full bg-white border-2 border-indigo-600 flex items-center justify-center font-extrabold text-[10px] text-indigo-600 shadow-xs">
                {stepItem.step}
              </div>

              {/* Event Card */}
              <div className="p-5 bg-white rounded-3xl border border-slate-200/80 shadow-xs space-y-2 hover:border-indigo-300 transition-all">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full border ${badgeClass}`}>
                      Step {stepItem.step}: {stepItem.element}
                    </span>
                    <h3 className="text-sm font-bold text-slate-900">
                      {stepItem.action}
                    </h3>
                  </div>
                  <span className="text-xs font-semibold text-slate-400">
                    {stepItem.timestamp}
                  </span>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed">
                  {stepItem.detail}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
