import React, { useState, useEffect } from 'react';
import { X, ChevronLeft, ChevronRight, Flame, Trophy, Calendar, Clock } from 'lucide-react';
import { studyService } from '../../services/studyService';

const INTENSITY_CLASSES = [
  'bg-slate-100 border-slate-200/70',
  'bg-indigo-200 border-indigo-300',
  'bg-indigo-400 border-indigo-500',
  'bg-indigo-600 border-indigo-700',
  'bg-purple-800 border-purple-900',
];

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export default function StreakCalendarModal({ isOpen, onClose, dailyGoalMinutes = 120 }) {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [activity, setActivity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hoveredDay, setHoveredDay] = useState(null);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) return;
    const load = async () => {
      try {
        setLoading(true);
        const res = await studyService.getYearlyActivity(year, dailyGoalMinutes);
        setActivity(res);
      } catch {
        setActivity(null);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [isOpen, year, dailyGoalMinutes]);

  if (!isOpen) return null;

  // Group days into 53-week columns (Sun-Sat)
  const weeks = [];
  if (activity?.days?.length) {
    let currentWeek = [];
    const firstDayOfWeek = new Date(activity.days[0].date + 'T00:00:00').getDay();
    for (let i = 0; i < firstDayOfWeek; i++) currentWeek.push(null);
    for (const d of activity.days) {
      currentWeek.push(d);
      if (currentWeek.length === 7) {
        weeks.push(currentWeek);
        currentWeek = [];
      }
    }
    if (currentWeek.length > 0) {
      while (currentWeek.length < 7) currentWeek.push(null);
      weeks.push(currentWeek);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 backdrop-blur-xs p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-4xl rounded-3xl bg-white p-6 shadow-2xl border border-slate-200 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Flame className="w-5 h-5 text-amber-500" />
              Study Activity &amp; Streak Calendar
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Daily Goal: {dailyGoalMinutes} mins • Only completed focus sessions count
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100"
            aria-label="Close calendar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Streak Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-2xl bg-amber-50/70 border border-amber-200/70 p-3">
            <div className="text-xs text-amber-700 font-semibold flex items-center gap-1">
              <Flame className="w-3.5 h-3.5" /> Current Streak
            </div>
            <div className="text-xl font-extrabold text-slate-900 mt-1">
              {activity?.currentStreak ?? 0} Days
            </div>
          </div>
          <div className="rounded-2xl bg-indigo-50/70 border border-indigo-200/70 p-3">
            <div className="text-xs text-indigo-700 font-semibold flex items-center gap-1">
              <Trophy className="w-3.5 h-3.5" /> Longest Streak
            </div>
            <div className="text-xl font-extrabold text-slate-900 mt-1">
              {activity?.longestStreak ?? 0} Days
            </div>
          </div>
          <div className="rounded-2xl bg-slate-50 border border-slate-200/70 p-3">
            <div className="text-xs text-slate-600 font-semibold flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" /> Active Days ({year})
            </div>
            <div className="text-xl font-extrabold text-slate-900 mt-1">
              {activity?.totalActiveDays ?? 0}
            </div>
          </div>
          <div className="rounded-2xl bg-slate-50 border border-slate-200/70 p-3">
            <div className="text-xs text-slate-600 font-semibold flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" /> Focused Hours
            </div>
            <div className="text-xl font-extrabold text-slate-900 mt-1">
              {activity?.totalFocusedHours ?? 0}h
            </div>
          </div>
        </div>

        {/* Year Navigation */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setYear((y) => y - 1)}
              className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50"
              aria-label="Previous year"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm font-bold text-slate-800">{year}</span>
            <button
              onClick={() => setYear((y) => Math.min(currentYear, y + 1))}
              disabled={year >= currentYear}
              className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
              aria-label="Next year"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
            <span>Less</span>
            {INTENSITY_CLASSES.map((cls, i) => (
              <span key={i} className={`w-3 h-3 rounded-xs border ${cls}`} />
            ))}
            <span>More</span>
          </div>
        </div>

        {/* Calendar Grid */}
        {loading ? (
          <div className="h-36 flex items-center justify-center">
            <div className="h-7 w-7 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
          </div>
        ) : (
          <div className="overflow-x-auto pb-2">
            <div className="inline-block min-w-full">
              <div className="flex text-[10px] text-slate-400 font-semibold mb-1 pl-7 justify-between">
                {MONTHS.map((m) => (
                  <span key={m}>{m}</span>
                ))}
              </div>
              <div className="flex gap-1">
                <div className="flex flex-col justify-between text-[10px] text-slate-400 pr-1.5 py-0.5">
                  <span>Sun</span>
                  <span>Wed</span>
                  <span>Sat</span>
                </div>
                <div className="flex gap-1">
                  {weeks.map((week, wIdx) => (
                    <div key={wIdx} className="flex flex-col gap-1">
                      {week.map((day, dIdx) =>
                        day ? (
                          <button
                            key={day.date}
                            type="button"
                            onMouseEnter={() => setHoveredDay(day)}
                            onFocus={() => setHoveredDay(day)}
                            aria-label={`${day.date}: ${day.minutes} minutes, ${day.sessionsCount} sessions`}
                            className={`w-3 h-3 rounded-xs border transition-transform hover:scale-125 ${INTENSITY_CLASSES[day.intensity || 0]}`}
                          />
                        ) : (
                          <span key={`empty_${wIdx}_${dIdx}`} className="w-3 h-3" />
                        )
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Hover Tooltip Bar */}
        <div className="min-h-8 rounded-xl bg-slate-50 border border-slate-200/70 px-3 py-2 text-xs text-slate-600 flex items-center justify-between">
          {hoveredDay ? (
            <>
              <span className="font-semibold text-slate-800">{hoveredDay.date}</span>
              <span>
                {hoveredDay.minutes} focused mins • {hoveredDay.sessionsCount} completed session{hoveredDay.sessionsCount === 1 ? '' : 's'} •{' '}
                {hoveredDay.goalMet ? 'Goal Achieved' : 'Goal Not Met'}
              </span>
            </>
          ) : (
            <span>Hover over any day square to inspect focused study minutes and completed sessions.</span>
          )}
        </div>
      </div>
    </div>
  );
}
