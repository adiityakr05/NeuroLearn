import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  LayoutDashboard,
  CalendarCheck,
  BookOpen,
  LineChart,
  Sparkles,
  ArrowRight
} from 'lucide-react';

export default function PlatformPreviewSection() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const previews = {
    dashboard: {
      title: 'Student Command Dashboard',
      desc: 'Central overview featuring active study streaks, daily target hours, upcoming exams, today’s adaptive tasks, and AI suggestions.',
      path: '/dashboard',
      features: ['Real-time retention progress', 'Adaptive schedule widget', 'Live task completion toggle'],
    },
    planner: {
      title: 'Adaptive Study Planner',
      desc: 'Calendar view balancing your cognitive load across 7 days, complete with rescheduling modal and spaced repetition queues.',
      path: '/planner',
      features: ['Daily & 7-Day calendar views', 'Rescheduling with decay impact warnings', 'Spaced repetition queue'],
    },
    subjects: {
      title: 'Curriculum & Mastery Manager',
      desc: 'Enrolled subjects with module breakdown, topic difficulty classifications (Easy/Medium/Hard), and full revision histories.',
      path: '/subjects',
      features: ['Color-coded subject cards', 'Difficulty and status filters', 'Spaced repetition history timelines'],
    },
    analytics: {
      title: 'Cognitive & Retention Analytics',
      desc: 'Ebbinghaus forgetting curve line charts, quiz accuracy trends, and subject mastery comparisons against benchmarks.',
      path: '/analytics',
      features: ['30-day Ebbinghaus decay curve', 'Predicted retention vs actual recall', 'Overdue memory review alerts'],
    },
  };

  const current = previews[activeTab];

  return (
    <section id="preview" className="py-20 bg-slate-50 border-t border-slate-200/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-12 space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
            Interactive Product Preview
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            Explore the Live Interface
          </h2>
          <p className="text-sm text-slate-500 leading-relaxed">
            Switch between modules to preview the tools built into the NeuroLearn platform.
          </p>

          {/* Tab Selector */}
          <div className="inline-flex items-center p-1.5 bg-slate-200/70 rounded-2xl gap-1 mt-4">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition ${
                activeTab === 'dashboard' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => setActiveTab('planner')}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition ${
                activeTab === 'planner' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Study Planner
            </button>
            <button
              onClick={() => setActiveTab('subjects')}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition ${
                activeTab === 'subjects' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Curriculum & Mastery
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition ${
                activeTab === 'analytics' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Retention Analytics
            </button>
          </div>
        </div>

        {/* Preview Card */}
        <div className="max-w-4xl mx-auto bg-white rounded-3xl border border-slate-200 shadow-xl p-8 space-y-6 text-left">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">Module Showcase</span>
              <h3 className="text-xl font-bold text-slate-900 mt-0.5">{current.title}</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-lg leading-relaxed">{current.desc}</p>
            </div>
            <Link
              to={current.path}
              className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition self-start sm:self-auto shrink-0 shadow-sm"
            >
              <span>Launch {activeTab}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {current.features.map((feat, i) => (
              <div key={i} className="p-3.5 rounded-2xl bg-slate-50 border border-slate-100 text-xs font-semibold text-slate-700 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-indigo-600 shrink-0"></span>
                <span>{feat}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
