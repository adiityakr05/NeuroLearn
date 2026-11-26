import React, { useState, useEffect } from 'react';
import { Sparkles, Calendar, BookOpen, AlertCircle, Plus, Filter, CheckCircle2 } from 'lucide-react';
import PlannerHeader from '../components/planner/PlannerHeader';
import WeekCalendarStrip from '../components/planner/WeekCalendarStrip';
import DailySessionCard from '../components/planner/DailySessionCard';
import RescheduleModal from '../components/planner/RescheduleModal';
import SpacedRepetitionSidebar from '../components/planner/SpacedRepetitionSidebar';
import { studyService } from '../services/studyService';

export default function StudyPlanner() {
  const getTodayStr = () => {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };

  const [selectedDate, setSelectedDate] = useState(getTodayStr);
  const [viewMode, setViewMode] = useState('day'); // 'day' | 'week'
  const [planData, setPlanData] = useState(null);
  const [weekSessions, setWeekSessions] = useState([]);
  const [spacedRepetitions, setSpacedRepetitions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal State
  const [rescheduleTarget, setRescheduleTarget] = useState(null);
  const [rescheduleModalOpen, setRescheduleModalOpen] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [subjects, setSubjects] = useState([]);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState(null);
  const [newSession, setNewSession] = useState({
    subjectId: '',
    topicId: '',
    title: '',
    date: getTodayStr(),
    timeSlot: '09:00 AM - 10:00 AM',
    durationMinutes: 45,
    notes: '',
  });

  // Filter State
  const [subjectFilter, setSubjectFilter] = useState('all');

  // Dynamic 7-day strip starting from today, with counts derived from real weekSessions
  const weekDates = React.useMemo(() => {
    const days = [];
    const base = new Date();
    for (let i = 0; i < 7; i++) {
      const d = new Date(base);
      d.setDate(base.getDate() + i);
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      const dateStr = `${y}-${m}-${day}`;
      const daySessions = weekSessions.filter((s) => s.date === dateStr);
      days.push({
        date: dateStr,
        dayShort: d.toLocaleDateString('en-US', { weekday: 'short' }),
        dayNum: String(d.getDate()),
        monthShort: d.toLocaleDateString('en-US', { month: 'short' }),
        tasksCount: daySessions.length,
        hasOverdue: daySessions.some((s) => s.isOverdue && s.status !== 'completed'),
      });
    }
    return days;
  }, [weekSessions]);

  const loadPlannerData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [dayPlan, allWeek, srQueue, subs] = await Promise.all([
        studyService.getStudyPlan(selectedDate),
        studyService.getWeekPlan(),
        studyService.getSpacedRepetitions(),
        studyService.getSubjects().catch(() => []),
      ]);
      setPlanData(dayPlan);
      setWeekSessions(allWeek);
      setSpacedRepetitions(srQueue);
      setSubjects(Array.isArray(subs) ? subs : []);
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

  const handleOpenCreateModal = () => {
    const firstSub = subjects[0];
    setNewSession({
      subjectId: firstSub?.id || '',
      topicId: firstSub?.topics?.[0]?.id || '',
      title: '',
      date: selectedDate,
      timeSlot: '09:00 AM - 10:00 AM',
      durationMinutes: 45,
      notes: '',
    });
    setCreateError(null);
    setCreateModalOpen(true);
  };

  const handleCreateSession = async (e) => {
    e.preventDefault();
    if (!newSession.subjectId) {
      setCreateError('Please select a subject.');
      return;
    }
    if (!newSession.date) {
      setCreateError('Please select a date.');
      return;
    }
    try {
      setCreating(true);
      setCreateError(null);
      await studyService.createStudySession({
        subject_id: newSession.subjectId,
        topic_id: newSession.topicId || null,
        date: newSession.date,
        time_slot: newSession.timeSlot || 'Flexible',
        duration_minutes: Number(newSession.durationMinutes) || 45,
        ai_reason: newSession.title.trim() || newSession.notes.trim() || 'Scheduled by student',
      });
      setCreateModalOpen(false);
      await loadPlannerData();
    } catch (err) {
      setCreateError(err.message || 'Failed to create study session');
    } finally {
      setCreating(false);
    }
  };

  const handleToday = () => {
    setSelectedDate(getTodayStr());
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
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-slate-500">
                {filteredSessions.length} session{filteredSessions.length !== 1 ? 's' : ''} listed
              </span>
              <button
                onClick={handleOpenCreateModal}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 transition"
              >
                <Plus className="w-3.5 h-3.5" /> New Session
              </button>
            </div>
          </div>

          {filteredSessions.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-3xl border border-slate-200/80 shadow-xs">
              <BookOpen className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <h3 className="text-base font-bold text-slate-800">No sessions scheduled for this day</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                No study sessions are scheduled for this date yet. Create a session to plan your study time.
              </p>
              <button
                onClick={handleOpenCreateModal}
                className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 transition"
              >
                <Plus className="w-4 h-4" /> Create Session
              </button>
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

      {/* Create Study Session Modal */}
      {createModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 backdrop-blur-xs p-4"
          onClick={() => setCreateModalOpen(false)}
        >
          <form
            onSubmit={handleCreateSession}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl border border-slate-200 space-y-4"
          >
            <h3 className="text-lg font-bold text-slate-900">Create Study Session</h3>
            {createError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
                {createError}
              </div>
            )}
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Subject *</label>
              <select
                value={newSession.subjectId}
                onChange={(e) => {
                  const sub = subjects.find((s) => s.id === e.target.value);
                  setNewSession((prev) => ({
                    ...prev,
                    subjectId: e.target.value,
                    topicId: sub?.topics?.[0]?.id || '',
                  }));
                }}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm bg-white"
                required
              >
                <option value="">Select a subject</option>
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Topic</label>
              <select
                value={newSession.topicId}
                onChange={(e) => setNewSession((prev) => ({ ...prev, topicId: e.target.value }))}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm bg-white"
              >
                <option value="">General Subject Review</option>
                {(subjects.find((s) => s.id === newSession.subjectId)?.topics || []).map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Session Title</label>
              <input
                type="text"
                value={newSession.title}
                onChange={(e) => setNewSession((prev) => ({ ...prev, title: e.target.value }))}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Date *</label>
                <input
                  type="date"
                  value={newSession.date}
                  onChange={(e) => setNewSession((prev) => ({ ...prev, date: e.target.value }))}
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Duration (mins) *</label>
                <input
                  type="number"
                  min={5}
                  max={480}
                  value={newSession.durationMinutes}
                  onChange={(e) => setNewSession((prev) => ({ ...prev, durationMinutes: e.target.value }))}
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Time Slot</label>
              <input
                type="text"
                value={newSession.timeSlot}
                onChange={(e) => setNewSession((prev) => ({ ...prev, timeSlot: e.target.value }))}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setCreateModalOpen(false)}
                className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={creating}
                className="px-5 py-2 rounded-xl bg-indigo-600 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {creating ? 'Saving...' : 'Save Session'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
