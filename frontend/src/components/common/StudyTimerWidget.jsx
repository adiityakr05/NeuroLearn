import React from 'react';
import { Play, Pause, CheckCircle2, X, Flame, Award } from 'lucide-react';
import { useTimer } from '../../context/TimerContext';

function formatTime(totalSec) {
  const s = Math.max(0, totalSec);
  const hrs = Math.floor(s / 3600);
  const mins = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  if (hrs > 0) {
    return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

export default function StudyTimerWidget() {
  const {
    activeTimer,
    elapsedSeconds,
    pauseTimer,
    resumeTimer,
    finishTimer,
    cancelTimer,
    celebrationData,
    dismissCelebration,
  } = useTimer();

  const displaySeconds = activeTimer
    ? activeTimer.mode === 'countdown'
      ? Math.max(0, activeTimer.plannedSeconds - elapsedSeconds)
      : elapsedSeconds
    : 0;

  const progressPct = activeTimer && activeTimer.plannedSeconds > 0
    ? Math.min(100, Math.round((elapsedSeconds / activeTimer.plannedSeconds) * 100))
    : 0;

  return (
    <>
      {activeTimer && (
        <div className="fixed bottom-5 right-5 z-50 w-80 rounded-2xl bg-slate-900 text-white shadow-2xl border border-indigo-500/40 p-4 space-y-3">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-300">
                {activeTimer.subjectName} • {activeTimer.isPaused ? 'Paused' : 'Focusing'}
              </span>
              <p className="text-sm font-bold truncate">{activeTimer.topicName}</p>
            </div>
            <button onClick={cancelTimer} className="text-slate-400 hover:text-rose-400" title="Cancel session">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-mono font-extrabold tracking-tight text-white">
              {formatTime(displaySeconds)}
            </span>
            <span className="text-xs text-slate-400">{progressPct}%</span>
          </div>

          <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-indigo-500 transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>

          <div className="flex items-center gap-2 pt-1">
            {activeTimer.isPaused ? (
              <button
                onClick={resumeTimer}
                className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-xl bg-indigo-600 py-2 text-xs font-semibold hover:bg-indigo-700"
              >
                <Play className="w-3.5 h-3.5" /> Resume
              </button>
            ) : (
              <button
                onClick={pauseTimer}
                className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-xl bg-slate-800 py-2 text-xs font-semibold hover:bg-slate-700"
              >
                <Pause className="w-3.5 h-3.5" /> Pause
              </button>
            )}
            <button
              onClick={finishTimer}
              className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-xl bg-emerald-600 py-2 text-xs font-semibold hover:bg-emerald-700"
            >
              <CheckCircle2 className="w-3.5 h-3.5" /> Finish
            </button>
          </div>
        </div>
      )}

      {celebrationData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <div className="max-w-sm w-full rounded-3xl bg-white p-6 text-center shadow-2xl border border-indigo-100 space-y-4">
            <div className="mx-auto w-16 h-16 rounded-full bg-amber-100 flex items-center justify-center motion-safe:animate-bounce">
              <Flame className="w-9 h-9 text-amber-500" />
            </div>
            <div>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-100 text-indigo-700">
                <Award className="w-3.5 h-3.5" /> Daily Study Goal Completed!
              </span>
              <h3 className="text-xl font-extrabold text-slate-900 mt-2">
                {celebrationData.streak}-Day Streak!
              </h3>
              <p className="text-sm text-slate-600 mt-1">
                Congratulations! You focused for {celebrationData.todayMinutes} minutes today and met your {celebrationData.dailyGoalMinutes}-minute goal.
              </p>
            </div>
            <button
              onClick={dismissCelebration}
              className="w-full rounded-xl bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
            >
              Keep Going
            </button>
          </div>
        </div>
      )}
    </>
  );
}
