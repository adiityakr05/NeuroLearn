/**
 * Data Normalization Layer
 * Provides clean, explicit mapping between FastAPI (snake_case)
 * and Frontend React models (camelCase) without destructive blanket transformations.
 */

export const normalizers = {
  // Normalize User payload
  user(data) {
    if (!data) return null;
    return {
      id: data.id || data.user_id,
      name: data.name || data.full_name || 'Aditya Kumar',
      email: data.email,
      program: data.program || data.academic_program || 'B.Tech Computer Science & AI',
      semester: data.semester || data.current_semester || 'Semester 6',
      avatar: data.avatar || data.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
    };
  },

  // Normalize Subject
  subject(data) {
    if (!data) return null;
    return {
      id: data.id || data.subject_id,
      name: data.name || data.subject_name,
      code: data.code || data.subject_code,
      color: data.color || data.theme_color || '#6366F1',
      description: data.description || '',
      topics: Array.isArray(data.topics) ? data.topics.map(normalizers.topic) : [],
    };
  },

  // Normalize Topic
  topic(data) {
    if (!data) return null;
    return {
      id: data.id || data.topic_id,
      subjectId: data.subjectId || data.subject_id,
      name: data.name || data.topic_name,
      difficulty: data.difficulty || 'Medium',
      mastery: Number(data.masteryScore ?? data.mastery ?? data.mastery_score ?? 50),
      retentionScore: Number(data.retentionScore ?? data.retention_score ?? 70),
      completed: Boolean(data.completed),
      lastRevised: data.lastRevised || data.last_revised || null,
      nextRevision: data.nextRevision || data.next_revision || null,
      revisionHistory: Array.isArray(data.revisionHistory || data.revision_history)
        ? (data.revisionHistory || data.revision_history)
        : [],
    };
  },

  // Normalize Study Session / Task
  studySession(data) {
    if (!data) return null;
    return {
      id: data.id || data.task_id || data.session_id,
      date: data.date,
      timeSlot: data.timeSlot || data.time_slot || `${data.start_time || ''} - ${data.end_time || ''}`.trim(),
      topic: data.topic || data.topic_name,
      subject: data.subject || data.subject_name,
      subjectCode: data.subjectCode || data.subject_code,
      durationMinutes: Number(data.durationMinutes ?? data.duration_minutes ?? 45),
      status: data.status || 'pending',
      priority: data.priority || 'medium',
      retentionScore: Number(data.retentionScore ?? data.retention_score ?? 70),
      repetitionCycle: data.repetitionCycle || data.repetition_cycle || 'Cycle 1',
      isOverdue: Boolean(data.isOverdue ?? data.is_overdue),
      aiReason: data.aiReason || data.ai_reason || 'Scheduled based on active learning agenda.',
    };
  },
};
