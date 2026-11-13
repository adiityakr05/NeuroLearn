import React, { useState, useEffect } from 'react';
import {
  BookOpen,
  Plus,
  Search,
  Filter,
  Sparkles,
  Layers,
  GraduationCap,
  AlertCircle,
  CheckCircle2
} from 'lucide-react';
import SubjectCard from '../components/subjects/SubjectCard';
import TopicRow from '../components/subjects/TopicRow';
import TopicDetailsModal from '../components/subjects/TopicDetailsModal';
import SubjectModal from '../components/subjects/SubjectModal';
import TopicModal from '../components/subjects/TopicModal';
import { studyService } from '../services/studyService';

export default function Subjects() {
  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('all'); // 'all' | 'Easy' | 'Medium' | 'Hard'
  const [statusFilter, setStatusFilter] = useState('all'); // 'all' | 'completed' | 'pending'

  // Modals state
  const [subjectModalOpen, setSubjectModalOpen] = useState(false);
  const [editingSubject, setEditingSubject] = useState(null);

  const [topicModalOpen, setTopicModalOpen] = useState(false);
  const [editingTopic, setEditingTopic] = useState(null);
  const [targetSubjectForTopic, setTargetSubjectForTopic] = useState(null);

  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [selectedTopicForDetails, setSelectedTopicForDetails] = useState(null);

  const fetchSubjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await studyService.getSubjects();
      setSubjects(res);
      if (selectedSubjectId === 'all' && res.length > 0) {
        // default to first subject or keep all
      }
    } catch (err) {
      setError(err.message || 'Failed to load subjects');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubjects();
  }, []);

  // --- SUBJECT HANDLERS ---
  const handleOpenAddSubject = () => {
    setEditingSubject(null);
    setSubjectModalOpen(true);
  };

  const handleOpenEditSubject = (subj) => {
    setEditingSubject(subj);
    setSubjectModalOpen(true);
  };

  const handleSaveSubject = async (formData) => {
    try {
      if (editingSubject) {
        await studyService.updateSubject(editingSubject.id, formData);
      } else {
        await studyService.addSubject(formData);
      }
      await fetchSubjects();
    } catch (err) {
      alert('Error saving subject: ' + err.message);
    }
  };

  const handleDeleteSubject = async (subjId) => {
    if (window.confirm('Are you sure you want to delete this subject and all its topics?')) {
      try {
        await studyService.deleteSubject(subjId);
        if (selectedSubjectId === subjId) {
          setSelectedSubjectId('all');
        }
        await fetchSubjects();
      } catch (err) {
        alert('Error deleting subject: ' + err.message);
      }
    }
  };

  // --- TOPIC HANDLERS ---
  const handleOpenAddTopic = (subjId) => {
    const parent = subjects.find((s) => s.id === subjId) || subjects[0];
    setTargetSubjectForTopic(parent);
    setEditingTopic(null);
    setTopicModalOpen(true);
  };

  const handleOpenEditTopic = (subjId, topic) => {
    const parent = subjects.find((s) => s.id === subjId);
    setTargetSubjectForTopic(parent);
    setEditingTopic(topic);
    setTopicModalOpen(true);
  };

  const handleSaveTopic = async (formData) => {
    try {
      if (!targetSubjectForTopic) return;
      if (editingTopic) {
        await studyService.updateTopic(targetSubjectForTopic.id, editingTopic.id, formData);
      } else {
        await studyService.addTopic(targetSubjectForTopic.id, formData);
      }
      await fetchSubjects();
    } catch (err) {
      alert('Error saving topic: ' + err.message);
    }
  };

  const handleDeleteTopic = async (subjId, topicId) => {
    if (window.confirm('Delete this topic?')) {
      try {
        await studyService.deleteTopic(subjId, topicId);
        await fetchSubjects();
      } catch (err) {
        alert('Error deleting topic: ' + err.message);
      }
    }
  };

  const handleToggleTopic = async (subjId, topicId) => {
    try {
      await studyService.toggleTopicCompletion(subjId, topicId);
      await fetchSubjects();
    } catch (err) {
      alert('Error toggling topic: ' + err.message);
    }
  };

  const handleViewTopicDetails = (topic) => {
    setSelectedTopicForDetails(topic);
    setDetailsModalOpen(true);
  };

  if (loading && subjects.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-3">
        <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
        <p className="text-xs font-semibold text-slate-500">
          Loading curriculum database and mastery metrics...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center bg-rose-50 border border-rose-200 rounded-2xl max-w-lg mx-auto my-10">
        <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
        <h3 className="text-base font-bold text-rose-900">Failed to load subjects</h3>
        <p className="text-xs text-rose-700 mt-1 mb-4">{error}</p>
        <button
          onClick={fetchSubjects}
          className="px-4 py-2 bg-rose-600 text-white rounded-xl text-xs font-semibold"
        >
          Retry
        </button>
      </div>
    );
  }

  // Flatten or filter topics based on active subject selection
  const visibleSubjects =
    selectedSubjectId === 'all'
      ? subjects
      : subjects.filter((s) => s.id === selectedSubjectId);

  // Collect all topic items with their parent subject reference for rendering
  const allTopicItems = visibleSubjects.flatMap((s) =>
    s.topics.map((t) => ({ ...t, parentSubjectId: s.id, parentSubjectName: s.name }))
  );

  // Apply Search, Difficulty, and Status filters
  const filteredTopics = allTopicItems.filter((item) => {
    const matchesSearch =
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.parentSubjectName.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesDiff = difficultyFilter === 'all' || item.difficulty === difficultyFilter;
    const matchesStatus =
      statusFilter === 'all' ||
      (statusFilter === 'completed' && item.completed) ||
      (statusFilter === 'pending' && !item.completed);
    return matchesSearch && matchesDiff && matchesStatus;
  });

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-200/80">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Curriculum & Mastery
            </h1>
            <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100">
              <Sparkles className="w-3.5 h-3.5" />
              Dynamic Mastery Tracking
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Manage your academic subjects, curate module topics, and inspect spaced repetition histories.
          </p>
        </div>

        <button
          onClick={handleOpenAddSubject}
          className="flex items-center gap-2 self-start sm:self-auto px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition shadow-xs"
        >
          <Plus className="w-4 h-4" />
          <span>Add New Subject</span>
        </button>
      </div>

      {/* Subjects Overview Carousel / Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-900">Enrolled Subjects</h2>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
              {subjects.length} Total
            </span>
          </div>

          <button
            onClick={() => setSelectedSubjectId('all')}
            className={`text-xs font-bold px-3 py-1 rounded-xl transition ${
              selectedSubjectId === 'all'
                ? 'bg-slate-900 text-white'
                : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            Show All Subjects
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {subjects.map((subj) => (
            <SubjectCard
              key={subj.id}
              subject={subj}
              isSelected={selectedSubjectId === subj.id}
              onSelect={() => setSelectedSubjectId(subj.id)}
              onEdit={handleOpenEditSubject}
              onDelete={handleDeleteSubject}
            />
          ))}
        </div>
      </div>

      {/* Topics Management Section */}
      <div className="bg-white rounded-3xl border border-slate-200/80 shadow-xs p-6 space-y-6">
        {/* Section Header & Search/Filters */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900">
              {selectedSubjectId === 'all'
                ? 'All Curriculum Topics'
                : `${subjects.find((s) => s.id === selectedSubjectId)?.name || 'Subject'} Topics`}
            </h3>
            <p className="text-xs text-slate-500">
              Showing {filteredTopics.length} of {allTopicItems.length} topics
            </p>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            {/* Search Input */}
            <div className="relative min-w-[200px] flex-1 sm:flex-initial">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search topics..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              />
            </div>

            {/* Difficulty Filter */}
            <select
              value={difficultyFilter}
              onChange={(e) => setDifficultyFilter(e.target.value)}
              className="py-1.5 px-3 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 focus:outline-none"
            >
              <option value="all">All Difficulties</option>
              <option value="Easy">Easy</option>
              <option value="Medium">Medium</option>
              <option value="Hard">Hard</option>
            </select>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="py-1.5 px-3 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 focus:outline-none"
            >
              <option value="all">All Status</option>
              <option value="completed">Completed</option>
              <option value="pending">Pending</option>
            </select>

            {/* Add Topic Button */}
            <button
              onClick={() =>
                handleOpenAddTopic(
                  selectedSubjectId === 'all' ? subjects[0]?.id : selectedSubjectId
                )
              }
              disabled={subjects.length === 0}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition shadow-2xs disabled:opacity-50"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Topic</span>
            </button>
          </div>
        </div>

        {/* Topics List */}
        {filteredTopics.length === 0 ? (
          <div className="p-12 text-center bg-slate-50/60 rounded-2xl border border-dashed border-slate-200">
            <Layers className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <h4 className="text-sm font-bold text-slate-700">No matching topics found</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Try adjusting your search query, difficulty filters, or select a different subject card above.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredTopics.map((topic) => (
              <TopicRow
                key={topic.id}
                topic={topic}
                onToggleComplete={() => handleToggleTopic(topic.parentSubjectId, topic.id)}
                onViewDetails={handleViewTopicDetails}
                onEdit={() => handleOpenEditTopic(topic.parentSubjectId, topic)}
                onDelete={() => handleDeleteTopic(topic.parentSubjectId, topic.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Modals */}
      <SubjectModal
        isOpen={subjectModalOpen}
        onClose={() => setSubjectModalOpen(false)}
        onSave={handleSaveSubject}
        editingSubject={editingSubject}
      />

      <TopicModal
        isOpen={topicModalOpen}
        onClose={() => setTopicModalOpen(false)}
        onSave={handleSaveTopic}
        editingTopic={editingTopic}
        subjectName={targetSubjectForTopic?.name}
      />

      <TopicDetailsModal
        isOpen={detailsModalOpen}
        onClose={() => setDetailsModalOpen(false)}
        topic={selectedTopicForDetails}
      />
    </div>
  );
}
