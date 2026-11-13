import axios from 'axios';
import { API_CONFIG } from '../config/apiConfig';

// Central Axios instance pointing to FastAPI backend
const api = axios.create({
  baseURL: API_CONFIG.baseURL,
  timeout: API_CONFIG.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: retrieve token from sessionStorage OR localStorage
api.interceptors.request.use(
  (config) => {
    const token =
      sessionStorage.getItem('neurolearn_token') ||
      localStorage.getItem('neurolearn_token') ||
      sessionStorage.getItem('neurolearn_demo_token') ||
      localStorage.getItem('neurolearn_demo_token');

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: unwrap FastAPI details and standardize error format
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // Check if error response comes with a FastAPI Pydantic detail string/array
    let message = 'An unexpected network error occurred';
    if (error.response?.data?.detail) {
      const detail = error.response.data.detail;
      message = Array.isArray(detail)
        ? detail.map((d) => d.msg || JSON.stringify(d)).join(', ')
        : String(detail);
    } else if (error.message) {
      message = error.message;
    }
    return Promise.reject(new Error(message));
  }
);

export default api;
