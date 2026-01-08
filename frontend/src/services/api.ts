import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = typeof window !== 'undefined' ? localStorage.getItem('authToken') : null;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      if (typeof window !== 'undefined') {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// API methods
export const api = {
  // Health check
  getHealth: async () => {
    const response = await apiClient.get('/api/health');
    return response.data;
  },

  // Students
  getStudents: async () => {
    const response = await apiClient.get('/api/students');
    return response.data;
  },

  createStudent: async (data: {
    email: string;
    firstName: string;
    lastName: string;
    passwordHash: string;
  }) => {
    const response = await apiClient.post('/api/students', data);
    return response.data;
  },

  getStudent: async (id: string) => {
    const response = await apiClient.get(`/api/students/${id}`);
    return response.data;
  },

  // Learning Paths
  getLearningPaths: async (studentId: string) => {
    const response = await apiClient.get(`/api/students/${studentId}/learning-paths`);
    return response.data;
  },

  createLearningPath: async (studentId: string, data: any) => {
    const response = await apiClient.post(`/api/students/${studentId}/learning-paths`, data);
    return response.data;
  },

  // Cognitive Metrics
  getCognitiveMetrics: async (studentId: string, params?: any) => {
    const response = await apiClient.get(`/api/students/${studentId}/cognitive-metrics`, { params });
    return response.data;
  },

  // Quiz Results
  submitQuizResult: async (studentId: string, moduleId: string, data: any) => {
    const response = await apiClient.post(`/api/students/${studentId}/quiz-results`, {
      moduleId,
      ...data,
    });
    return response.data;
  },
};

export default apiClient;
