import React from 'react';
import { Sparkles, Calendar, BookOpen, LineChart } from 'lucide-react';

export function PlaceholderPage({ title, description, icon: Icon }) {
  return (
    <div className="p-8 sm:p-12 text-center bg-white rounded-2xl border border-slate-200/80 shadow-xs max-w-2xl mx-auto my-8">
      <div className="w-16 h-16 rounded-2xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center mx-auto mb-4">
        {Icon ? <Icon className="w-8 h-8" /> : <Sparkles className="w-8 h-8" />}
      </div>
      <h2 className="text-xl font-bold text-slate-900">{title}</h2>
      <p className="text-sm text-slate-500 mt-2 max-w-md mx-auto leading-relaxed">
        {description}
      </p>
      <div className="mt-6 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100 text-xs font-semibold text-slate-600">
        <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
        <span>Scheduled for Phase 4 UI Buildout</span>
      </div>
    </div>
  );
}

export function StudyPlannerPage() {
  return (
    <PlaceholderPage
      title="Adaptive Study Planner"
      description="Daily personalized study agenda, task rescheduling, and spaced repetition calendar."
      icon={Calendar}
    />
  );
}

export function SubjectsPage() {
  return (
    <PlaceholderPage
      title="Subjects & Topics Management"
      description="Track topic mastery, configure difficulty ratings, and inspect spaced repetition histories."
      icon={BookOpen}
    />
  );
}

export function AnalyticsPage() {
  return (
    <PlaceholderPage
      title="Performance Analytics & Memory Decay"
      description="Retention curves, quiz trends, and cognitive weakness identification powered by ML models."
      icon={LineChart}
    />
  );
}

export function RecommendationsPage() {
  return (
    <PlaceholderPage
      title="AI Recommendations Hub"
      description="Deep dive into the Critic and Problem Generator elements driving your personalized schedule."
      icon={Sparkles}
    />
  );
}
