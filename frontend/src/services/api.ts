import axios, { AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || (
  process.env.NODE_ENV === 'development' 
    ? 'http://localhost:5001/api'  // Direct backend URL for development
    : '/api'  // Proxy for production
);

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error: AxiosError) => {
    console.error('API Error:', error.response?.data || error.message);
    
    if (error.response?.status === 404) {
      // Handle not found errors
      return Promise.reject({
        ...error,
        userMessage: 'Resource not found'
      });
    }
    
    if (error.response?.status && error.response.status >= 500) {
      // Handle server errors
      return Promise.reject({
        ...error,
        userMessage: 'Server error occurred. Please try again.'
      });
    }
    
    return Promise.reject(error);
  }
);

export default api;
