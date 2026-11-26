import React from 'react';
import { BrainCircuit, Cpu, Sparkles, CheckCircle2, AlertCircle, Info } from 'lucide-react';

export default function AgentArchitectureHeader({ agentStatus, activeTab, onTabChange }) {
  if (!agentStatus) return null;

  const tabs = [
    { id: 'performance', label: '1. Performance Element', count: 4 },
    { id: 'critic', label: '2. Critic Element', count: 3 },
    { id: 'learning', label: '3. Learning Element', count: 3 },
    { id: 'generator', label: '4. Problem Generator', count: 3 },
    { id: 'timeline', label: 'Agent Loop Trace', count: null },
  ];

  return (
    <div className="space-y-6">
      {/* Title & System Status Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-6 border-b border-slate-200/80">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-md shadow-indigo-100">
              <BrainCircuit className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                  Adaptive Learning Agent Hub
                </h1>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Online
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
                Inspect the 4-element cognitive architecture orchestrating your study planning.
              </p>
            </div>
          </div>
        </div>

        {/* Live Agent Cycle State */}
        <div className="flex items-center gap-3 bg-white p-2.5 rounded-2xl border border-slate-200 shadow-2xs self-start lg:self-auto text-xs">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-xl bg-indigo-50 text-indigo-700 font-semibold">
            <span className="w-2 h-2 rounded-full bg-indigo-600 animate-ping"></span>
            <span>Agent Cycle: Continuous</span>
          </div>
          <span className="text-slate-400">•</span>
          <span className="text-slate-500 font-medium">Last calibrated: {agentStatus.lastCalibration}</span>
        </div>
      </div>

      {/* Prototype / Simulated Demo Notice */}
      <div className="p-4 rounded-2xl bg-amber-50/70 border border-amber-200/80 flex items-start gap-3 text-xs text-amber-900">
        <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">Prototype Demonstration & AI Architecture Transparency:</span>
          <p className="text-amber-800/90 mt-0.5 leading-relaxed">
            This hub renders the live operational logic of NeuroLearn's learning agent. While recommendations and scheduling rules reflect real heuristics, neural weight updates and retention predictions will transition from simulation to live Python/FastAPI execution once Member 2 and Member 3 deploy the AI backend.
          </p>
        </div>
      </div>

      {/* Element Status Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {agentStatus.activeElements.map((elem, i) => (
          <div
            key={elem.name}
            className="p-3.5 bg-white rounded-2xl border border-slate-200/80 text-xs space-y-1 shadow-2xs"
          >
            <div className="flex items-center justify-between">
              <span className="font-extrabold text-slate-900">{elem.name}</span>
              <span className="w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-emerald-100"></span>
            </div>
            <p className="text-slate-500 line-clamp-2 text-[11px] leading-relaxed">{elem.status}</p>
          </div>
        ))}
      </div>

      {/* Element Tabs Navigation */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-slate-200 text-xs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`px-3.5 py-2.5 rounded-xl font-bold transition flex items-center gap-2 shrink-0 ${
              activeTab === tab.id
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <span>{tab.label}</span>
            {tab.count !== null && (
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full font-extrabold ${
                  activeTab === tab.id
                    ? 'bg-white/20 text-white'
                    : 'bg-slate-200 text-slate-700'
                }`}
              >
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
