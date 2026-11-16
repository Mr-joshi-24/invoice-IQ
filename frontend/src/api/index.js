import apiClient from './client';

// Authentication & Users
export const loginUser = (credentials) => {
  return apiClient.post('/auth/login', credentials);
};

export const registerUser = (userData) => {
  return apiClient.post('/auth/register', userData);
};

export const getCurrentUser = () => {
  return apiClient.get('/auth/me');
};

// Documents & Pipeline
export const getDocuments = (params = {}) => {
  return apiClient.get('/documents', { params });
};

export const getDocument = (id) => {
  return apiClient.get(`/documents/${id}`);
};

export const uploadDocuments = (formData, onUploadProgress) => {
  return apiClient.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress
  });
};

export const reprocessDocument = (id) => {
  return apiClient.post(`/documents/${id}/process`);
};

export const submitReview = (id, reviewData) => {
  return apiClient.post(`/documents/${id}/review`, reviewData);
};

export const getPagePreviewUrl = (id, page = 1) => {
  return `/api/v1/documents/${id}/preview/${page}`;
};

// Analytics & Metrics
export const getAnalyticsOverview = () => {
  return apiClient.get('/analytics/overview');
};

export const getModelMetrics = () => {
  return apiClient.get('/analytics/model');
};

// Settings
export const getSettings = () => {
  return apiClient.get('/settings');
};

export const updateSettings = (data) => {
  return apiClient.put('/settings', data);
};

export const getExportUrl = (format = 'csv', status = '') => {
  const query = status ? `&status=${status}` : '';
  return `/api/v1/documents/export/download?format=${format}${query}`;
};
