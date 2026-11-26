import React from 'react';
import {
  CalendarCheck,
  Repeat,
  Brain,
  Layers,
  LineChart,
  Sparkles,
} from 'lucide-react';

export default function FeaturesSection() {
  const features = [
    {
      title: 'Adaptive Study Planner',
      desc: 'Generates daily study slots and full 7-day calendars with interactive completion tracking and rescheduling.',
      icon: CalendarCheck,
      color: 'text-indigo-600 bg-indigo-50 border-indigo-100',
    },
    {
      title: 'Spaced Repetition Engine',
      desc: 'Systematically spaces review sessions at mathematical intervals to arrest memory decay before exams.',
      icon: Repeat,
      color: 'text-emerald-600 bg-emerald-50 border-emerald-100',
    },
    {
      title: 'Memory Retention Curves',
      desc: 'Visualizes your personal Ebbinghaus forgetting trajectory over 30 days compared against baseline retention.',
      icon: Brain,
      color: 'text-violet-600 bg-violet-50 border-violet-100',
    },
    {
      title: 'Topic Mastery Tracking',
      desc: 'Maintains granular mastery ratings across all curriculum modules, highlighting strong and weak topics.',
      icon: Layers,
      color: 'text-cyan-600 bg-cyan-50 border-cyan-100',
    },
    {
      title: 'Performance Analytics',
      desc: 'Detailed Recharts graphs comparing quiz accuracy over time against class cohort averages.',
      icon: LineChart,
      color: 'text-amber-600 bg-amber-50 border-amber-100',
    },
    {
      title: 'Explainable AI Insights',
      desc: 'Every scheduled session and recommendation explicitly discloses the underlying machine learning logic.',
      icon: Sparkles,
      color: 'text-rose-600 bg-rose-50 border-rose-100',
    },
  ];

  return (
    <section id="features" className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
            Platform Capabilities
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            Engineered for Cognitive Retention
          </h2>
          <p className="text-sm text-slate-500 leading-relaxed">
            Every feature in NeuroLearn is designed to maximize memory persistence and streamline exam readiness.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="p-6 bg-slate-50/70 rounded-3xl border border-slate-200/80 hover:bg-white hover:border-indigo-300 hover:shadow-md transition-all space-y-3"
              >
                <div
                  className={`w-12 h-12 rounded-2xl border flex items-center justify-center ${f.color}`}
                >
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="text-base font-bold text-slate-900">{f.title}</h3>
                <p className="text-xs text-slate-600 leading-relaxed">{f.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
