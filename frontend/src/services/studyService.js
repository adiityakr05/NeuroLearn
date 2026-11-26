import api from './api';
import { API_CONFIG } from '../config/apiConfig';
import { normalizers } from './normalizers';
import {
  mockDashboard,
  mockUser,
  mockWeekSchedule,
  mockSpacedRepetitions,
  mockSubjects,
  mockAnalyticsData,
  mockRecommendationsHubData,
} from './mockData';

// Mutable in-memory state for mock sessions during active sessions
let activeSessions = [...mockWeekSchedule];
let activeRepetitions = [...mockSpacedRepetitions];
let activeSubjects = JSON.parse(JSON.stringify(mockSubjects));

export const studyService = {
  // ==========================================
  // 1. DASHBOARD MODULE
  // ==========================================
  async getDashboardData() {
    if (API_CONFIG.useMock.dashboard) {
      await new Promise((resolve) => setTimeout(resolve, 250));
      // Sync today tasks based on active sessions
      const todayTasks = activeSessions.filter((t) => t.date === '2026-11-13');
      const completedCount = todayTasks.filter((t) => t.status === 'completed').length;
      return {
        ...mockDashboard,
        todaySchedule: todayTasks,
        stats: {
          ...mockDashboard.stats,
          completedSessions: completedCount,
          pendingTasks: Math.max(0, todayTasks.length - completedCount),
        },
      };
    }

    const data = await api.get('/dashboard');
    return {
      stats: data.stats,
      upcomingExams: data.upcomingExams || data.upcoming_exams || [],
      subjectMastery: data.subjectMastery || data.subject_mastery || [],
      weeklyActivity: data.weeklyActivity || data.weekly_activity || [],
      aiRecommendations: data.aiRecommendations || data.ai_recommendations || [],
      todaySchedule: Array.isArray(data.todaySchedule || data.today_schedule)
        ? (data.todaySchedule || data.today_schedule).map(normalizers.studySession)
        : [],
    };
  },

  // ==========================================
  // 2. STUDY PLANNER MODULE
  // ==========================================
  async getStudyPlan(date = '2026-11-13') {
    if (API_CONFIG.useMock.planner) {
      await new Promise((resolve) => setTimeout(resolve, 200));
      const filtered = activeSessions.filter((s) => s.date === date);
      return {
        date,
        sessions: filtered,
        totalSessions: filtered.length,
        completedSessions: filtered.filter((s) => s.status === 'completed').length,
        totalMinutes: filtered.reduce((acc, curr) => acc + curr.durationMinutes, 0),
      };
    }

    const res = await api.get(`/study-plan?date=${date}`);
    return {
      date: res.date || date,
      totalSessions: res.totalSessions ?? res.total_sessions ?? res.sessions?.length ?? 0,
      completedSessions: res.completedSessions ?? res.completed_sessions ?? 0,
      totalMinutes: res.totalMinutes ?? res.total_minutes ?? 0,
      sessions: Array.isArray(res.sessions) ? res.sessions.map(normalizers.studySession) : [],
    };
  },

  async getWeekPlan() {
    if (API_CONFIG.useMock.planner) {
      await new Promise((resolve) => setTimeout(resolve, 200));
      return [...activeSessions];
    }

    const res = await api.get('/study-plan/week');
    return Array.isArray(res) ? res.map(normalizers.studySession) : [];
  },

  async toggleTaskStatus(taskId, newStatus, actualDurationMinutes = null) {
    if (API_CONFIG.useMock.planner) {
      await new Promise((resolve) => setTimeout(resolve, 150));
      activeSessions = activeSessions.map((t) =>
        t.id === taskId ? { ...t, status: newStatus, actualDurationMinutes: actualDurationMinutes ?? t.actualDurationMinutes } : t
      );
      return { success: true, taskId, newStatus };
    }

    return api.post('/study-plan/complete', { taskId, status: newStatus, actual_duration_minutes: actualDurationMinutes });
  },

  async startStudySession(sessionId) {
    const res = await api.post(`/study-sessions/${sessionId}/start`);
    return normalizers.studySession(res);
  },

  async completeStudySession(sessionId, actualDurationMinutes = null) {
    const res = await api.post(`/study-sessions/${sessionId}/complete`, { actual_duration_minutes: actualDurationMinutes });
    return normalizers.studySession(res);
  },

  async abandonStudySession(sessionId, actualDurationMinutes = null, reason = null) {
    const res = await api.post(`/study-sessions/${sessionId}/abandon`, { actual_duration_minutes: actualDurationMinutes, reason });
    return normalizers.studySession(res);
  },

  async rescheduleTask(taskId, newDate, newSlot, reason) {
    if (API_CONFIG.useMock.planner) {
      await new Promise((resolve) => setTimeout(resolve, 250));
      let foundTask = null;
      activeSessions = activeSessions.map((t) => {
        if (t.id === taskId) {
          foundTask = {
            ...t,
            date: newDate,
            timeSlot: newSlot,
            aiReason: `Rescheduled by student: "${reason}". AI recalculated slot to preserve minimum retention decay.`,
          };
          return foundTask;
        }
        return t;
      });
      return { success: true, task: foundTask };
    }

    const res = await api.post('/study-plan/reschedule', { taskId, newDate, newSlot, reason });
    return { success: true, task: normalizers.studySession(res.task || res) };
  },

  async getSpacedRepetitions() {
    if (API_CONFIG.useMock.planner) {
      await new Promise((resolve) => setTimeout(resolve, 150));
      return [...activeRepetitions];
    }

    const res = await api.get('/spaced-repetition');
    return res;
  },

  // ==========================================
  // 3. SUBJECTS & TOPICS MODULE
  // ==========================================
  async getSubjects() {
    if (API_CONFIG.useMock.subjects) {
      await new Promise((resolve) => setTimeout(resolve, 250));
      return JSON.parse(JSON.stringify(activeSubjects));
    }

    const res = await api.get('/subjects');
    return Array.isArray(res) ? res.map(normalizers.subject) : [];
  },

  async addSubject(subjectData) {
    if (API_CONFIG.useMock.subjects) {
      await new Promise((resolve) => setTimeout(resolve, 250));
      const newSubject = {
        id: `sub_${Date.now()}`,
        name: subjectData.name,
        code: subjectData.code || 'CS' + Math.floor(600 + Math.random() * 99),
        color: subjectData.color || '#6366F1',
        description: subjectData.description || 'Custom student-curated curriculum.',
        topics: [],
      };
      activeSubjects.unshift(newSubject);
      return { success: true, subject: newSubject };
    }

    const res = await api.post('/subjects', subjectData);
    return { success: true, subject: normalizers.subject(res.subject || res) };
  },

  async updateSubject(subjectId, updatedData) {
    if (API_CONFIG.useMock.subjects) {
      await new Promise((resolve) => setTimeout(resolve, 200));
      activeSubjects = activeSubjects.map((s) =>
        s.id === subjectId ? { ...s, ...updatedData } : s
      );
      return { success: true };
    }

    return api.put(`/subjects/${subjectId}`, updatedData);
  },

  async deleteSubject(subjectId) {
    if (API_CONFIG.useMock.subjects) {
      await new Promise((resolve) => setTimeout(resolve, 200));
      activeSubjects = activeSubjects.filter((s) => s.id !== subjectId);
      return { success: true };
    }

    return api.delete(`/subjects/${subjectId}`);
  },

  async addTopic(subjectId, topicData) {
    if (API_CONFIG.useMock.subjects) {
      await new Promise((resolve) => setTimeout(resolve, 250));
      const newTopic = {
        id: `top_${Date.now()}`,
        name: topicData.name,
        difficulty: topicData.difficulty || 'Medium',
        mastery: Number(topicData.mastery) || 50,
        completed: Boolean(topicData.completed),
        lastRevised: topicData.lastRevised || '2026-11-13',
        nextRevision: topicData.nextRevision || '2026-11-20',
        revisionHistory: [
          {
            date: '2026-11-13',
            score: Number(topicData.mastery) || 50,
            intervalDays: 0,
            note: 'Topic added to study curriculum.',
          },
        ],
      };
      activeSubjects = activeSubjects.map((s) =>
        s.id === subjectId ? { ...s, topics: [newTopic, ...s.topics] } : s
      );
      return { success: true, topic: newTopic };
    }

    const res = await api.post(`/subjects/${subjectId}/topics`, topicData);
    return { success: true, topic: normalizers.topic(res.topic || res) };
  },

  async updateTopic(subjectId, topicId, updatedData) {
    if (API_CONFIG.useMock.subjects) {
      await new Promise((resolve) => setTimeout(resolve, 200));
      activeSubjects = activeSubjects.map((s) => {
        if (s.id === subjectId) {
          const updatedTopics = s.topics.map((t) =>
            t.id === topicId ? { ...t, ...updatedData } : t
          );
          return { ...s, topics: updatedTopics };
        }
        return s;
      });
      return { success: true };
    }

    return api.put(`/subjects/${subjectId}/topics/${topicId}`, updatedData);
  },

  async deleteTopic(subjectId, topicId) {
    if (API_CONFIG.useMock.subjects) {
      await new Promise((resolve) => setTimeout(resolve, 200));
      activeSubjects = activeSubjects.map((s) => {
        if (s.id === subjectId) {
          return { ...s, topics: s.topics.filter((t) => t.id !== topicId) };
        }
        return s;
      });
      return { success: true };
    }

    return api.delete(`/subjects/${subjectId}/topics/${topicId}`);
  },

  async toggleTopicCompletion(subjectId, topicId, completed) {
    if (API_CONFIG.useMock.subjects) {
      await new Promise((resolve) => setTimeout(resolve, 150));
      activeSubjects = activeSubjects.map((s) => {
        if (s.id === subjectId) {
          const updatedTopics = s.topics.map((t) =>
            t.id === topicId ? { ...t, completed: !t.completed } : t
          );
          return { ...s, topics: updatedTopics };
        }
        return s;
      });
      return { success: true };
    }

    const res = await api.patch(`/topics/${topicId}`, { completed });
    return normalizers.topic(res);
  },

  // ==========================================
  // 4. ANALYTICS MODULE
  // ==========================================
  async getAnalyticsData(timeRange = '30d') {
    if (API_CONFIG.useMock.analytics) {
      await new Promise((resolve) => setTimeout(resolve, 250));
      return { ...mockAnalyticsData };
    }

    const res = await api.get(`/analytics/history?timeRange=${timeRange}`);
    // If backend returns a packaged frontend_bundle, use it; otherwise fall back to raw res
    return res.frontend_bundle || res;
  },

  // ==========================================
  // 5. AI RECOMMENDATIONS & 4-ELEMENT HUB
  // ==========================================
  async getRecommendationsHubData() {
    if (API_CONFIG.useMock.recommendations) {
      await new Promise((resolve) => setTimeout(resolve, 250));
      return JSON.parse(JSON.stringify(mockRecommendationsHubData));
    }

    return api.get('/recommendations/hub');
  },

  async acceptRecommendation(recId) {
    if (API_CONFIG.useMock.recommendations) {
      await new Promise((resolve) => setTimeout(resolve, 150));
      return { success: true, recId, message: 'Recommendation scheduled.' };
    }

    return api.post(`/recommendations/${recId}/accept`);
  },

  async dismissRecommendation(recId) {
    if (API_CONFIG.useMock.recommendations) {
      await new Promise((resolve) => setTimeout(resolve, 150));
      return { success: true, recId, message: 'Recommendation dismissed.' };
    }

    return api.post(`/recommendations/${recId}/dismiss`);
  },

  // ==========================================
  // 6. DIAGNOSTIC ACTIVITIES MODULE
  // ==========================================
  async startDiagnosticActivity(activityId) {
    if (API_CONFIG.useMock.diagnostic) {
      await new Promise((resolve) => setTimeout(resolve, 150));
      return { success: true, activityId, message: 'Diagnostic probe started.' };
    }

    return api.post(`/diagnostic-activities/${activityId}/start`);
  },

  // User profile fallback helper
  async getCurrentUser() {
    if (API_CONFIG.useMock.user) {
      return { ...mockUser };
    }
    const res = await api.get('/user/profile');
    return normalizers.user(res);
  },

  // ==========================================
  // 7. QUIZ SUBMISSION MODULE (WITH IDEMPOTENCY)
  // ==========================================
  async createStudySession(sessionData) {
    const res = await api.post('/study-sessions', sessionData);
    return normalizers.studySession(res);
  },

  async deleteStudySession(sessionId) {
    return api.delete(`/study-sessions/${sessionId}`);
  },

  async generateQuiz(topicId, difficulty = 'Medium', numQuestions = 5) {
    return api.post('/quiz-attempts/generate', {
      topic_id: topicId,
      difficulty,
      num_questions: numQuestions,
    });
  },

  async getQuizAttempts(topicId = null) {
    const query = topicId ? `?topic_id=${topicId}` : '';
    return api.get(`/quiz-attempts${query}`);
  },

  async getNotifications() {
    return api.get('/notifications');
  },

  async markNotificationRead(id) {
    return api.patch(`/notifications/${id}/read`);
  },

  async markAllNotificationsRead() {
    return api.patch('/notifications/read-all');
  },

  async dismissNotification(id) {
    return api.delete(`/notifications/${id}`);
  },

  async getYearlyActivity(year = new Date().getFullYear(), dailyGoalMinutes = 120) {
    return api.get(`/dashboard/activity?year=${year}&daily_goal_minutes=${dailyGoalMinutes}`);
  },

  async submitQuizAttempt(quizData, idempotencyKey = null) {
    // Generate a client UUID for every new quiz submission if not explicitly provided
    const key = idempotencyKey || (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `quiz_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`);
    const headers = { 'Idempotency-Key': key };
    const res = await api.post('/quiz-attempts', quizData, { headers });
    return res;
  },
};
