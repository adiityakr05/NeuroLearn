import React from 'react';
import { Link } from 'react-router-dom';
import {
  Brain,
  ArrowRight,
  Sparkles,
  CalendarCheck,
  LineChart,
  Repeat,
  CheckCircle2,
  Clock,
  ShieldCheck
} from 'lucide-react';

export default function HeroSection() {
  return (
    <section className="relative overflow-hidden pt-12 pb-20 lg:pt-20 lg:pb-28">
      {/* Background Subtle Gradient Accents */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-gradient-to-b from-indigo-50/60 to-transparent pointer-events-none -z-10" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto space-y-6">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 border border-indigo-100 text-xs font-bold text-indigo-700 shadow-2xs">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>AI-Powered Adaptive Learning Agent</span>
            <span className="text-slate-300">•</span>
            <span className="text-slate-500 font-medium">B.Tech Capstone Architecture</span>
          </div>

          {/* Headline & Tagline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 tracking-tight leading-[1.15]">
            Learn Smarter. <br className="hidden sm:inline" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-indigo-700 to-violet-600">
              Remember Longer.
            </span>
          </h1>

          {/* Subtext */}
          <p className="text-base sm:text-lg text-slate-600 leading-relaxed font-normal">
            NeuroLearn is an intelligent learning platform that continuously adapts your study schedule based on memory retention decay, topic mastery, and upcoming exam deadlines.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            <Link
              to="/dashboard"
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl text-sm font-bold transition shadow-md shadow-indigo-100"
            >
              <span>Explore Student Dashboard</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href="#agent-architecture"
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3.5 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 rounded-2xl text-sm font-bold transition shadow-xs"
            >
              <span>How the Agent Works</span>
            </a>
          </div>

          {/* Micro trust indicators */}
          <div className="flex items-center justify-center gap-6 pt-4 text-xs font-semibold text-slate-500 flex-wrap">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              Spaced Repetition
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              Explainable AI Decisions
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              Dynamic Forgetting Curves
            </span>
          </div>
        </div>

        {/* Product Preview Mockup */}
        <div className="mt-14 max-w-5xl mx-auto rounded-3xl bg-white border border-slate-200/90 shadow-2xl p-4 sm:p-6 space-y-4">
          {/* Mock Window Top Bar */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-rose-400"></span>
              <span className="w-3 h-3 rounded-full bg-amber-400"></span>
              <span className="w-3 h-3 rounded-full bg-emerald-400"></span>
              <span className="text-xs font-semibold text-slate-400 ml-2">neurolearn.app/dashboard</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold text-indigo-600 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-100">
                Live Agent Actuation
              </span>
            </div>
          </div>

          {/* Mock Dashboard Snippet */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-left">
            {/* Stat Pill 1 */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-bold text-slate-400 uppercase">Today's Target</span>
              <p className="text-2xl font-extrabold text-slate-900 mt-0.5">3.5h / 5.0h</p>
              <p className="text-xs text-emerald-600 font-semibold mt-1">+45m ahead of schedule</p>
            </div>
            {/* Stat Pill 2 */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-bold text-slate-400 uppercase">Overall Retention</span>
              <p className="text-2xl font-extrabold text-slate-900 mt-0.5">82%</p>
              <p className="text-xs text-indigo-600 font-semibold mt-1">Spaced Repetition Calibrated</p>
            </div>
            {/* Stat Pill 3 */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-bold text-slate-400 uppercase">Upcoming Exam</span>
              <p className="text-2xl font-extrabold text-slate-900 mt-0.5">In 11 Days</p>
              <p className="text-xs text-rose-600 font-semibold mt-1">CS601: Machine Learning</p>
            </div>
          </div>

          {/* AI Explainability Highlight Box */}
          <div className="p-4 rounded-2xl bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-left">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-xl bg-white/10 shrink-0">
                <Brain className="w-5 h-5 text-indigo-300" />
              </div>
              <div>
                <p className="text-xs font-bold text-indigo-200 uppercase tracking-wider">
                  Adaptive Agent Decision
                </p>
                <p className="text-sm font-semibold text-white mt-0.5">
                  "Prioritizing Support Vector Machines today: Predicted memory retention dropped to 52% with exam in 11 days."
                </p>
              </div>
            </div>
            <Link
              to="/planner"
              className="px-3.5 py-1.5 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-bold shrink-0 self-start sm:self-auto transition"
            >
              View Plan
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
