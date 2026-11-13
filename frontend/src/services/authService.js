import api from './api';
import { API_CONFIG } from '../config/apiConfig';
import { normalizers } from './normalizers';

const TOKEN_KEY = 'neurolearn_token';
const USER_KEY = 'neurolearn_user';

export const authService = {
  // Login method supporting both mock and real API
  async login({ email, password, rememberMe }) {
    if (API_CONFIG.useMock.auth) {
      await new Promise((resolve) => setTimeout(resolve, 350));
      const user = {
        id: 'usr_01',
        name: email.split('@')[0].replace('.', ' ').replace(/\b\w/g, (c) => c.toUpperCase()) || 'Aditya Kumar',
        email: email.trim().toLowerCase(),
        avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
        currentSemester: 'Semester 6',
        program: 'B.Tech Computer Science & AI',
      };
      const mockToken = `demo_token_${Date.now()}_${Math.random().toString(36).substring(2)}`;
      const storage = rememberMe ? localStorage : sessionStorage;
      storage.setItem(TOKEN_KEY, mockToken);
      storage.setItem(USER_KEY, JSON.stringify(user));
      return { user, token: mockToken };
    }

    // Real API integration
    const res = await api.post('/auth/login', { email, password });
    const token = res.accessToken || res.access_token || res.token;
    const user = normalizers.user(res.user);

    const storage = rememberMe ? localStorage : sessionStorage;
    storage.setItem(TOKEN_KEY, token);
    storage.setItem(USER_KEY, JSON.stringify(user));
    return { user, token };
  },

  // Register method
  async register({ fullName, email, password, program }) {
    if (API_CONFIG.useMock.auth) {
      await new Promise((resolve) => setTimeout(resolve, 400));
      const user = {
        id: `usr_${Date.now()}`,
        name: fullName.trim(),
        email: email.trim().toLowerCase(),
        avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
        currentSemester: 'Semester 6',
        program: program?.trim() || 'B.Tech Computer Science & AI',
      };
      const mockToken = `demo_token_${Date.now()}_${Math.random().toString(36).substring(2)}`;
      sessionStorage.setItem(TOKEN_KEY, mockToken);
      sessionStorage.setItem(USER_KEY, JSON.stringify(user));
      return { user, token: mockToken };
    }

    // Real API integration
    const res = await api.post('/auth/register', {
      fullName,
      email,
      password,
      program,
    });
    const token = res.accessToken || res.access_token || res.token;
    const user = normalizers.user(res.user);

    sessionStorage.setItem(TOKEN_KEY, token);
    sessionStorage.setItem(USER_KEY, JSON.stringify(user));
    return { user, token };
  },

  // User profile
  async getCurrentUserProfile() {
    if (API_CONFIG.useMock.user) {
      return authService.getCurrentUser();
    }
    const res = await api.get('/user/profile');
    return normalizers.user(res);
  },

  // Logout student: strictly clears both sessionStorage and localStorage
  logout() {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    // Legacy cleanup
    sessionStorage.removeItem('neurolearn_demo_token');
    sessionStorage.removeItem('neurolearn_demo_user');
    localStorage.removeItem('neurolearn_demo_token');
    localStorage.removeItem('neurolearn_demo_user');
  },

  // Retrieve locally cached user profile
  getCurrentUser() {
    try {
      const stored = sessionStorage.getItem(USER_KEY) || localStorage.getItem(USER_KEY);
      if (stored) return JSON.parse(stored);
    } catch {
      // return null if parsing fails
    }
    return null;
  },

  // Check token existence in either storage location
  isAuthenticated() {
    return Boolean(
      sessionStorage.getItem(TOKEN_KEY) ||
      localStorage.getItem(TOKEN_KEY) ||
      sessionStorage.getItem('neurolearn_demo_token') ||
      localStorage.getItem('neurolearn_demo_token')
    );
  },
};
