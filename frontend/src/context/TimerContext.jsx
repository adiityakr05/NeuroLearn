import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { studyService } from '../services/studyService';

const TimerContext = createContext(null);
const TIMER_STORAGE_KEY = 'neurolearn_active_timer';
const GOAL_STORAGE_KEY = 'neurolearn_daily_goal_minutes';
const CELEBRATION_STORAGE_KEY = 'neurolearn_goal_celebrated_date';

export function TimerProvider({ children }) {
  const [activeTimer, setActiveTimer] = useState(() => {
    try {
      const saved = localStorage.getItem(TIMER_STORAGE_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [dailyGoalMinutes, setDailyGoalMinutes] = useState(() => {
    const saved = localStorage.getItem(GOAL_STORAGE_KEY);
    return saved ? Number(saved) : 120;
  });
  const [nowMs, setNowMs] = useState(Date.now());
  const [celebrationData, setCelebrationData] = useState(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (activeTimer) {
      localStorage.setItem(TIMER_STORAGE_KEY, JSON.stringify(activeTimer));
    } else {
      localStorage.removeItem(TIMER_STORAGE_KEY);
    }
  }, [activeTimer]);

  useEffect(() => {
    if (activeTimer && !activeTimer.isPaused) {
      intervalRef.current = setInterval(() => setNowMs(Date.now()), 1000);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [activeTimer?.isPaused, activeTimer?.sessionId]);

  const updateDailyGoal = (minutes) => {
    const clamped = Math.max(15, Math.min(720, Number(minutes) || 120));
    setDailyGoalMinutes(clamped);
    localStorage.setItem(GOAL_STORAGE_KEY, String(clamped));
  };

  const getElapsedSeconds = () => {
    if (!activeTimer) return 0;
    const accumulated = activeTimer.accumulatedSeconds || 0;
    if (activeTimer.isPaused || !activeTimer.lastResumedAt) return accumulated;
    return accumulated + Math.max(0, Math.floor((nowMs - activeTimer.lastResumedAt) / 1000));
  };

  const startTimer = async ({
    subjectId,
    subjectName,
    topicId,
    topicName,
    title,
    durationMinutes = 25,
    mode = 'countdown',
    existingSessionId = null,
    recommendationId = null,
  }) => {
    if (activeTimer) {
      const ok = window.confirm('A study timer is already running. Discard it and start a new session?');
      if (!ok) return false;
    }

    const todayStr = new Date().toISOString().split('T')[0];
    let sessionId = existingSessionId;
    try {
      if (!sessionId && subjectId) {
        const created = await studyService.createStudySession({
          subject_id: subjectId,
          topic_id: topicId || null,
          date: todayStr,
          duration_minutes: durationMinutes,
          ai_reason: title || 'Focused study timer session',
        });
        sessionId = created.id;
      }
      if (sessionId) {
        await studyService.startStudySession(sessionId);
      }
    } catch {
      // Allow local timer to run even if offline/session already started
    }

    setNowMs(Date.now());
    setActiveTimer({
      sessionId,
      recommendationId,
      subjectId,
      subjectName: subjectName || 'Study Session',
      topicId,
      topicName: topicName || title || 'Focused Practice',
      title: title || topicName || 'Focused Study',
      mode,
      plannedSeconds: durationMinutes * 60,
      accumulatedSeconds: 0,
      lastResumedAt: Date.now(),
      isPaused: false,
      startedAt: new Date().toISOString(),
    });
    return true;
  };

  const pauseTimer = () => {
    if (!activeTimer || activeTimer.isPaused) return;
    const elapsed = getElapsedSeconds();
    setActiveTimer((prev) => ({
      ...prev,
      accumulatedSeconds: elapsed,
      lastResumedAt: null,
      isPaused: true,
    }));
  };

  const resumeTimer = () => {
    if (!activeTimer || !activeTimer.isPaused) return;
    setNowMs(Date.now());
    setActiveTimer((prev) => ({
      ...prev,
      lastResumedAt: Date.now(),
      isPaused: false,
    }));
  };

  const finishTimer = async () => {
    if (!activeTimer) return null;
    const elapsedSec = getElapsedSeconds();
    const actualMinutes = Math.max(1, Math.round(elapsedSec / 60));

    try {
      if (activeTimer.sessionId) {
        await studyService.completeStudySession(activeTimer.sessionId, actualMinutes);
      }
      if (activeTimer.recommendationId) {
        await studyService.acceptRecommendation(activeTimer.recommendationId).catch(() => {});
      }
    } catch {
      // Ignore if already completed
    }

    // Check if daily goal was just reached today
    try {
      const dash = await studyService.getDashboardData();
      const todayMinutes = Math.round((dash?.stats?.todayStudyHours || 0) * 60);
      const todayStr = new Date().toISOString().split('T')[0];
      const alreadyCelebrated = localStorage.getItem(CELEBRATION_STORAGE_KEY) === todayStr;
      if (todayMinutes >= dailyGoalMinutes && !alreadyCelebrated) {
        localStorage.setItem(CELEBRATION_STORAGE_KEY, todayStr);
        setCelebrationData({
          streak: dash?.stats?.activeStreak || 1,
          todayMinutes,
          dailyGoalMinutes,
        });
      }
    } catch {
      // Non-blocking
    }

    setActiveTimer(null);
    return actualMinutes;
  };

  const cancelTimer = async () => {
    if (!activeTimer) return;
    const ok = window.confirm('Cancel this active study session? Paused/cancelled time will not count toward your study goal.');
    if (!ok) return;
    try {
      if (activeTimer.sessionId) {
        await studyService.abandonStudySession(activeTimer.sessionId, 0, 'Cancelled by student');
      }
    } catch {
      // Non-blocking
    }
    setActiveTimer(null);
  };

  return (
    <TimerContext.Provider
      value={{
        activeTimer,
        elapsedSeconds: getElapsedSeconds(),
        dailyGoalMinutes,
        updateDailyGoal,
        startTimer,
        pauseTimer,
        resumeTimer,
        finishTimer,
        cancelTimer,
        celebrationData,
        dismissCelebration: () => setCelebrationData(null),
      }}
    >
      {children}
    </TimerContext.Provider>
  );
}

export function useTimer() {
  return useContext(TimerContext);
}
