import React from 'react';
import { ArrowRight, UserCheck, ShieldCheck, Cpu, CalendarCheck, HelpCircle } from 'lucide-react';

export default function HowItWorksSection() {
  const steps = [
    {
      step: '1',
      title: 'Student Input',
      desc: 'You enroll your subjects, schedule examination dates, and input available study hours.',
      icon: UserCheck,
    },
    {
      step: '2',
      title: 'Performance Evaluation',
      desc: 'The Critic evaluates completed tasks, session adherence, and recent diagnostic quiz scores.',
      icon: ShieldCheck,
    },
    {
      step: '3',
      title: 'Knowledge Calibration',
      desc: 'The Learning Element recalculates Ebbinghaus forgetting curves and updates your topic mastery.',
      icon: Cpu,
    },
    {
      step: '4',
      title: 'Schedule Adaptation',
      desc: 'The Performance Element adjusts upcoming study slots, re-prioritizing decaying concepts.',
      icon: CalendarCheck,
    },
    {
      step: '5',
      title: 'Active Probing',
      desc: 'The Problem Generator synthesizes targeted active recall drills to close comprehension gaps.',
      icon: HelpCircle,
    },
  ];

  return (
    <section id="how-it-works" className="py-20 bg-slate-50 border-t border-slate-200/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
            Continuous Closed-Loop
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            How the Adaptive Agent Operates
          </h2>
          <p className="text-sm text-slate-500 leading-relaxed">
            Every study session you complete or test you take triggers a 5-step feedback cycle that continuously personalizes your academic preparation.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {steps.map((st, idx) => {
            const Icon = st.icon;
            return (
              <div
                key={st.step}
                className="p-5 bg-white rounded-3xl border border-slate-200/80 shadow-xs flex flex-col justify-between space-y-3 relative"
              >
                <div>
                  <div className="w-10 h-10 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-sm mb-3">
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                    Step 0{st.step}
                  </span>
                  <h3 className="text-base font-bold text-slate-900 mt-0.5">{st.title}</h3>
                  <p className="text-xs text-slate-500 mt-2 leading-relaxed">{st.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
