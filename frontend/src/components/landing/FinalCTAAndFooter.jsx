import React from 'react';
import { Link } from 'react-router-dom';
import { BrainCircuit, ArrowRight, GitBranch, GraduationCap } from 'lucide-react';

export default function FinalCTAAndFooter() {
  return (
    <div>
      {/* Final Call to Action */}
      <section className="py-20 bg-gradient-to-br from-indigo-900 via-indigo-800 to-slate-900 text-white relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6 relative z-10">
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-300 px-3 py-1 rounded-full bg-white/10 border border-white/10 inline-block">
            Start Learning Smarter
          </span>
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight">
            Stop Guessing Your Study Timetable. <br />
            Let Cognitive AI Guide Your Mastery.
          </h2>
          <p className="text-sm sm:text-base text-indigo-200/90 max-w-xl mx-auto leading-relaxed">
            Experience personalized spaced repetition, automated exam prioritization, and explainable recommendations today.
          </p>

          <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              to="/dashboard"
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-3.5 bg-white text-indigo-900 hover:bg-indigo-50 rounded-2xl text-sm font-extrabold transition shadow-lg"
            >
              <span>Launch NeuroLearn App</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Modern Academic Footer */}
      <footer className="bg-white border-t border-slate-200/80 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            {/* Brand */}
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-xs">
                <BrainCircuit className="w-5 h-5" />
              </div>
              <div>
                <span className="font-bold text-base text-slate-900">NeuroLearn</span>
                <p className="text-xs text-slate-500">Adaptive Learning Agent for Personalised Study Planning</p>
              </div>
            </div>

            {/* Quick Links */}
            <div className="flex items-center gap-6 text-xs font-semibold text-slate-600 flex-wrap">
              <Link to="/dashboard" className="hover:text-indigo-600 transition">
                Student Dashboard
              </Link>
              <Link to="/planner" className="hover:text-indigo-600 transition">
                Adaptive Planner
              </Link>
              <Link to="/subjects" className="hover:text-indigo-600 transition">
                Curriculum
              </Link>
              <Link to="/analytics" className="hover:text-indigo-600 transition">
                Analytics
              </Link>
              <Link to="/recommendations" className="hover:text-indigo-600 transition">
                Agent Hub
              </Link>
            </div>
          </div>

          <div className="border-t border-slate-100 pt-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-slate-400">
            <div className="flex items-center gap-1.5 text-slate-500">
              <GraduationCap className="w-4 h-4 text-indigo-500" />
              <span>B.Tech AI Capstone Project • Member 1 (Frontend Development)</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1 text-slate-500">
                <GitBranch className="w-3.5 h-3.5 text-indigo-600" />
                <span>Branch: feature/frontend</span>
              </span>
              <span>© 2026 NeuroLearn. All rights reserved.</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
