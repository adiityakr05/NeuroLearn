// Granular API and Mock Configuration for NeuroLearn
// Allows each domain module to independently switch between mock implementations
// and real FastAPI endpoints during incremental integration.

export const API_CONFIG = {
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 10000,
  useMock: {
    // All modules default to true (mock mode) unless explicitly set to 'false' in .env
    auth: import.meta.env.VITE_MOCK_AUTH !== 'false',
    user: import.meta.env.VITE_MOCK_USER !== 'false',
    dashboard: import.meta.env.VITE_MOCK_DASHBOARD !== 'false',
    subjects: import.meta.env.VITE_MOCK_SUBJECTS !== 'false',
    planner: import.meta.env.VITE_MOCK_PLANNER !== 'false',
    analytics: import.meta.env.VITE_MOCK_ANALYTICS !== 'false',
    recommendations: import.meta.env.VITE_MOCK_RECOMMENDATIONS !== 'false',
    diagnostic: import.meta.env.VITE_MOCK_DIAGNOSTIC !== 'false',
  },
};
