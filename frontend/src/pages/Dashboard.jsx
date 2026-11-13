import React, { useState, useEffect } from 'react';
import {
  Clock,
  CheckCircle2,
  ListTodo,
  TrendingUp,
  Sparkles,
  Flame,
  Brain,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import StatCard from '../components/dashboard/StatCard';
import AIRecommendationCard from '../components/dashboard/AIRecommendationCard';
import TodayScheduleWidget from '../components/dashboard/TodayScheduleWidget';
import WeeklyActivityChart from '../components/dashboard/WeeklyActivityChart';
import UpcomingExamsWidget from '../components/dashboard/UpcomingExamsWidget';
import { studyService } from '../services/studyService';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [bannerVisible, setBannerVisible] = useState(true);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await studyService.getDashboardData();
      setData(res);
    } catch (err) {
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleToggleTask = async (taskId, newStatus) => {
    try {
      await studyService.toggleTaskStatus(taskId, newStatus);
      // Refresh local state to reflect instant change
      setData((prev) => {
        if (!prev) return prev;
        const updatedSchedule = prev.todaySchedule.map((t) =>
          t.id === taskId ? { ...t, status: newStatus } : t
        );
        const completedCount = updatedSchedule.filter((t) => t.status === 'completed').length;
        return {
          ...prev,
          todaySchedule: updatedSchedule,
          stats: {
            ...prev.stats,
            completedSessions: completedCount,
            pendingTasks: Math.max(0, updatedSchedule.length - completedCount),
          },
        };
      });
    } catch (err) {
      alert('Failed to update task status: ' + err.message);
    }
  };

  const handleRecommendationAction = (rec) => {
    alert(`AI Action Triggered: "${rec.title}" has been applied to your study agenda.`);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-12 h-12 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
        <p className="text-sm font-semibold text-slate-600 animate-pulse">
          NeuroLearn Agent is calibrating your retention model...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center bg-rose-50 border border-rose-200 rounded-2xl max-w-xl mx-auto my-12">
        <AlertCircle className="w-10 h-10 text-rose-500 mx-auto mb-3" />
        <h3 className="text-lg font-bold text-rose-900">Failed to load dashboard</h3>
        <p className="text-sm text-rose-700 mt-1 mb-4">{error}</p>
        <button
          onClick={fetchDashboardData}
          className="px-4 py-2 bg-rose-600 text-white rounded-xl text-sm font-semibold hover:bg-rose-700 transition"
        >
          Try Again
        </button>
      </div>
    );
  }

  const { stats, upcomingExams, weeklyActivity, aiRecommendations, todaySchedule } = data;

  return (
    <div className="space-y-8">
      {/* Welcome & Overview Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Welcome back, Aditya 👋
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Your retention score is steady at <strong className="text-slate-800">82%</strong>. The Critic element adjusted 2 tasks today for maximum exam impact.
          </p>
        </div>

        <button
          onClick={fetchDashboardData}
          className="flex items-center gap-2 self-start sm:self-auto px-4 py-2.5 bg-white border border-slate-200 text-slate-700 rounded-xl text-xs font-semibold hover:bg-slate-50 hover:border-slate-300 transition shadow-2xs"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Sync Learning State</span>
        </button>
      </div>

      {/* AI Agent Highlight Banner */}
      {bannerVisible && (
        <div className="relative overflow-hidden p-5 rounded-2xl bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white shadow-md">
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className="p-2.5 rounded-xl bg-white/10 backdrop-blur-md border border-white/10 shrink-0">
                <Brain className="w-6 h-6 text-indigo-300" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/30 text-indigo-200 border border-indigo-400/20">
                    Adaptive Planner Note
                  </span>
                  <span className="text-xs text-indigo-200">Exam Countdown: 11 Days</span>
                </div>
                <p className="text-sm sm:text-base font-semibold mt-1 text-white">
                  Machine Learning exam is approaching. Focus has been shifted toward low-retention topics.
                </p>
                <p className="text-xs text-indigo-200/90 mt-0.5">
                  Algorithm adjusted today's schedule to prioritize Support Vector Machines before memory decay accelerates.
                </p>
              </div>
            </div>
            <button
              onClick={() => setBannerVisible(false)}
              className="text-xs text-indigo-300 hover:text-white self-end md:self-center font-medium underline"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Today's Study Hours"
          value={`${stats.todayStudyHours}h`}
          subtitle={`Target: ${stats.todayTargetHours}h / day`}
          icon={Clock}
          colorScheme="indigo"
          trend="+45m vs yesterday"
        />
        <StatCard
          title="Completed Sessions"
          value={stats.completedSessions}
          subtitle={`${stats.pendingTasks} pending tasks today`}
          icon={CheckCircle2}
          colorScheme="emerald"
        />
        <StatCard
          title="Overall Retention Progress"
          value={`${stats.overallProgress}%`}
          subtitle="Based on spaced repetition checks"
          icon={TrendingUp}
          colorScheme="cyan"
          trend="+3.2% this week"
        />
        <StatCard
          title="Study Streak"
          value={`${stats.activeStreak} Days`}
          subtitle="Consistent study habit"
          icon={Flame}
          colorScheme="amber"
        />
      </div>

      {/* AI Recommendations Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Explainable AI Recommendations</h2>
              <p className="text-xs text-slate-500">Autonomous suggestions derived from your mastery & retention signals</p>
            </div>
          </div>
          <span className="text-xs font-semibold text-indigo-600 bg-indigo-50 border border-indigo-100 px-2.5 py-1 rounded-full">
            {aiRecommendations.length} Actions Ready
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {aiRecommendations.map((rec) => (
            <AIRecommendationCard
              key={rec.id}
              recommendation={rec}
              onAction={handleRecommendationAction}
            />
          ))}
        </div>
      </div>

      {/* Schedule and Upcoming Exams Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <TodayScheduleWidget
            tasks={todaySchedule}
            onToggleTask={handleToggleTask}
          />
        </div>
        <div>
          <UpcomingExamsWidget exams={upcomingExams} />
        </div>
      </div>

      {/* Weekly Activity Trend */}
      <div>
        <WeeklyActivityChart data={weeklyActivity} />
      </div>
    </div>
  );
}
