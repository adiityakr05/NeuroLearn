import React, { useState, useEffect } from 'react';
import { Sparkles, Calendar, BookOpen, AlertCircle, Plus, Filter, CheckCircle2 } from 'lucide-react';
import PlannerHeader from '../components/planner/PlannerHeader';
import WeekCalendarStrip from '../components/planner/WeekCalendarStrip';
import DailySessionCard from '../components/planner/DailySessionCard';
import RescheduleModal from '../components/planner/RescheduleModal';
import SpacedRepetitionSidebar from '../components/planner/SpacedRepetitionSidebar';
import { studyService } from '../services/studyService';

export default function StudyPlanner() {
  const [selectedDate, setSelectedDate] = useState('2026-11-13');
  const [viewMode, setViewMode] = useState('day'); // 'day' | 'week'
  const [planData, setPlanData] = useState(null);
  const [weekSessions, setWeekSessions] = useState([]);
  const [spacedRepetitions, setSpacedRepetitions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal State
  const [rescheduleTarget, setRescheduleTarget] = useState(null);
  const [rescheduleModalOpen, setRescheduleModalOpen] = useState(false);

  // Filter State
  const [subjectFilter, setSubjectFilter] = useState('all');

  // Hardcoded 7-day strip based on current mock week
  const weekDates = [
    { date: '2026-11-13', dayShort: 'Fri', dayNum: '13', monthShort: 'Nov', tasksCount: 5, hasOverdue: true },
    { date: '2026-11-14', dayShort: 'Sat', dayNum: '14', monthShort: 'Nov', tasksCount: 3, hasOverdue: false },
    { date: '2026-11-15', dayShort: 'Sun', dayNum: '15', monthShort: 'Nov', tasksCount: 2, hasOverdue: true },
    { date: '2026-11-16', dayShort: 'Mon', dayNum: '16', monthShort: 'Nov', tasksCount: 2, hasOverdue: false },
    { date: '2026-11-17', dayShort: 'Tue', dayNum: '17', monthShort: 'Nov', tasksCount: 0, hasOverdue: false },
    { date: '2026-11-18', dayShort: 'Wed', dayNum: '18', monthShort: 'Nov', tasksCount: 0, hasOverdue: false },
    { date: '2026-11-19', dayShort: 'Thu', dayNum: '19', monthShort: 'Nov', tasksCount: 0, hasOverdue: false },
  ];

  const loadPlannerData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [dayPlan, allWeek, srQueue] = await Promise.all([
        studyService.getStudyPlan(selectedDate),
        studyService.getWeekPlan(),
        studyService.getSpacedRepetitions(),
      ]);
      setPlanData(dayPlan);
      setWeekSessions(allWeek);
      setSpacedRepetitions(srQueue);
    } catch (err) {
      setError(err.message || 'Failed to load study plan');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPlannerData();
  }, [selectedDate]);

  // Navigate between days
  const handlePrevDay = () => {
    const currentIndex = weekDates.findIndex((d) => d.date === selectedDate);
    if (currentIndex > 0) {
      setSelectedDate(weekDates[currentIndex - 1].date);
    }
  };

  const handleNextDay = () => {
    const currentIndex = weekDates.findIndex((d) => d.date === selectedDate);
    if (currentIndex >= 0 && currentIndex < weekDates.length - 1) {
      setSelectedDate(weekDates[currentIndex + 1].date);
    }
  };

  const handleToday = () => {
    setSelectedDate('2026-11-13');
  };

  // Toggle status handler
  const handleToggleStatus = async (taskId, newStatus) => {
    try {
      await studyService.toggleTaskStatus(taskId, newStatus);
      // Update local state
      setPlanData((prev) => {
        if (!prev) return prev;
        const updated = prev.sessions.map((s) =>
          s.id === taskId ? { ...s, status: newStatus } : s
        );
        return {
          ...prev,
          sessions: updated,
          completedSessions: updated.filter((s) => s.status === 'completed').length,
        };
      });
      setWeekSessions((prev) =>
        prev.map((s) => (s.id === taskId ? { ...s, status: newStatus } : s))
      );
    } catch (err) {
      alert('Error updating session status: ' + err.message);
    }
  };

  // Reschedule handler
  const handleOpenReschedule = (session) => {
    setRescheduleTarget(session);
    setRescheduleModalOpen(true);
  };

  const handleConfirmReschedule = async (taskId, newDate, newSlot, reason) => {
    try {
      await studyService.rescheduleTask(taskId, newDate, newSlot, reason);
      // Reload planner for fresh date views
      await loadPlannerData();
    } catch (err) {
      alert('Reschedule error: ' + err.message);
    }
  };

  if (loading && !planData) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-3">
        <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
        <p className="text-xs font-semibold text-slate-500">
          Synthesizing optimal study slots from the Performance Element...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center bg-rose-50 border border-rose-200 rounded-2xl max-w-lg mx-auto my-10">
        <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
        <h3 className="text-base font-bold text-rose-900">Failed to load study plan</h3>
        <p className="text-xs text-rose-700 mt-1 mb-4">{error}</p>
        <button
          onClick={loadPlannerData}
          className="px-4 py-2 bg-rose-600 text-white rounded-xl text-xs font-semibold"
        >
          Retry
        </button>
      </div>
    );
  }

  // Active sessions based on view mode
  const displayedSessions =
    viewMode === 'day'
      ? planData?.sessions || []
      : weekSessions;

  // Filtered by subject
  const filteredSessions =
    subjectFilter === 'all'
      ? displayedSessions
      : displayedSessions.filter((s) => s.subject === subjectFilter);

  // Available subjects for filter pills
  const availableSubjects = [
    'all',
    ...new Set(displayedSessions.map((s) => s.subject)),
  ];

  const totalMinutes = displayedSessions.reduce((acc, curr) => acc + curr.durationMinutes, 0);
  const totalHours = (totalMinutes / 60).toFixed(1);
  const completedCount = displayedSessions.filter((s) => s.status === 'completed').length;

  return (
    <div className="space-y-6">
      {/* Top Header Navigation */}
      <PlannerHeader
        currentDate={selectedDate}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onPrev={handlePrevDay}
        onNext={handleNextDay}
        onToday={handleToday}
        totalSessions={displayedSessions.length}
        completedSessions={completedCount}
        totalHours={totalHours}
      />

      {/* Week Calendar Strip (always visible for rapid day switching) */}
      <WeekCalendarStrip
        selectedDate={selectedDate}
        onSelectDate={(date) => {
          setSelectedDate(date);
          setViewMode('day');
        }}
        weekDates={weekDates}
      />

      {/* Subject Filter Pills Strip */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span className="text-slate-400 font-semibold uppercase tracking-wider text-[11px] flex items-center gap-1 shrink-0">
          <Filter className="w-3.5 h-3.5" />
          <span>Filter:</span>
        </span>
        {availableSubjects.map((sub) => (
          <button
            key={sub}
            onClick={() => setSubjectFilter(sub)}
            className={`px-3 py-1.5 rounded-xl font-bold capitalize transition shrink-0 ${
              subjectFilter === sub
                ? 'bg-slate-900 text-white shadow-xs'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {sub === 'all' ? 'All Subjects' : sub}
          </button>
        ))}
      </div>

      {/* Main Grid: Sessions List & Spaced Repetition Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sessions Column */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">
              {viewMode === 'day' ? 'Scheduled Learning Sessions' : '7-Day Weekly Curriculum'}
            </h2>
            <span className="text-xs font-semibold text-slate-500">
              {filteredSessions.length} session{filteredSessions.length !== 1 ? 's' : ''} listed
            </span>
          </div>

          {filteredSessions.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-3xl border border-slate-200/80 shadow-xs">
              <BookOpen className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <h3 className="text-base font-bold text-slate-800">No sessions scheduled for this day</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                The Performance Element determined this as an optimal recovery slot, or all tasks have been completed.
              </p>
            </div>
          ) : (
            <div className="space-y-3.5">
              {filteredSessions.map((session) => (
                <DailySessionCard
                  key={session.id}
                  session={session}
                  onToggleStatus={handleToggleStatus}
                  onOpenReschedule={handleOpenReschedule}
                />
              ))}
            </div>
          )}
        </div>

        {/* Spaced Repetition Queue Panel */}
        <div>
          <SpacedRepetitionSidebar items={spacedRepetitions} />
        </div>
      </div>

      {/* Interactive Reschedule Modal */}
      <RescheduleModal
        session={rescheduleTarget}
        isOpen={rescheduleModalOpen}
        onClose={() => {
          setRescheduleModalOpen(false);
          setRescheduleTarget(null);
        }}
        onConfirm={handleConfirmReschedule}
      />
    </div>
  );
}
