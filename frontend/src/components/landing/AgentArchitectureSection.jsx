import React from 'react';
import { Play, CheckCircle2, Cpu, HelpCircle, ArrowRight } from 'lucide-react';

export default function AgentArchitectureSection() {
  const elements = [
    {
      number: '01',
      name: 'Performance Element',
      role: 'Schedule Synthesis & Action Formulation',
      badge: 'Action Actuator',
      badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      description:
        'Takes student availability, examination countdowns, and topic priorities to generate the optimal daily study sequence with realistic time durations.',
      highlight: 'Generates daily study slots and priorities.',
    },
    {
      number: '02',
      name: 'Critic Element',
      role: 'Performance Auditing & Plan Evaluation',
      badge: 'Audit & Feedback',
      badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200',
      description:
        'Continuously compares expected test scores against actual quiz results. Audits whether the student followed recommendations and detects cognitive burnout.',
      highlight: 'Validates whether study plans actually worked.',
    },
    {
      number: '03',
      name: 'Learning Element',
      role: 'Model Adaptation & Memory Decay Calibration',
      badge: 'Cognitive Calibration',
      badgeColor: 'bg-cyan-50 text-cyan-700 border-cyan-200',
      description:
        'Improves the agent knowledge base over time. Calibrates individual topic decay parameters (λ) and personalizes spaced repetition intervals for each student.',
      highlight: 'Learns how fast you forget each topic.',
    },
    {
      number: '04',
      name: 'Problem Generator',
      role: 'Exploration & Diagnostic Activity Formulation',
      badge: 'Active Exploration',
      badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
      description:
        'Formulates light diagnostic quizzes and active recall challenges designed to uncover hidden learning bottlenecks and test model certainty.',
      highlight: 'Probes areas where student mastery is uncertain.',
    },
  ];

  return (
    <section id="agent-architecture" className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
            System Architecture
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            The 4-Element Learning-Agent Architecture
          </h2>
          <p className="text-sm text-slate-500 leading-relaxed">
            NeuroLearn is engineered around Russell & Norvig's canonical learning agent framework, transforming passive study lists into an intelligent cognitive feedback loop.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {elements.map((elem) => (
            <div
              key={elem.number}
              className="p-6 bg-slate-50/70 rounded-3xl border border-slate-200/80 hover:border-indigo-300 hover:bg-white hover:shadow-md transition-all flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-2xl font-black text-indigo-600/30">
                    {elem.number}
                  </span>
                  <span
                    className={`text-[10px] font-extrabold uppercase px-2.5 py-0.5 rounded-full border ${elem.badgeColor}`}
                  >
                    {elem.badge}
                  </span>
                </div>

                <h3 className="text-lg font-bold text-slate-900">{elem.name}</h3>
                <span className="text-xs font-semibold text-slate-500 block">
                  {elem.role}
                </span>

                <p className="text-xs text-slate-600 leading-relaxed pt-1">
                  {elem.description}
                </p>
              </div>

              <div className="pt-3 border-t border-slate-200/60 text-[11px] font-semibold text-indigo-900">
                ⚡ {elem.highlight}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
