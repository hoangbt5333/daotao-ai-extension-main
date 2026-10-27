// API Configuration
export const API_CONFIG = {
  BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000",
  API_BASE_PATH: "/api/v1",
  TIMEOUT: 30000, // 30 seconds
};

// API Endpoints
export const API_ENDPOINTS = {
  // Core endpoints
  ROOT: "/",
  HEALTH: "/health",
  PROVIDERS: `${API_CONFIG.API_BASE_PATH}/providers/`,
  
  // Upload & Analysis
  UPLOAD: `${API_CONFIG.API_BASE_PATH}/upload/`,
  ANALYZE: `${API_CONFIG.API_BASE_PATH}/analyze/`,
  MAPPING_PDFS: `${API_CONFIG.API_BASE_PATH}/mapping/pdfs`,
  
  // Outline endpoints
  OUTLINE_IMPORT: `${API_CONFIG.API_BASE_PATH}/outline/import-excel`,
  OUTLINE_TEMPLATE: `${API_CONFIG.API_BASE_PATH}/outline/template`,
  
  // Question Processing
  QUESTIONS_PROCESS: `${API_CONFIG.API_BASE_PATH}/questions/process`,
  QUESTIONS_FROM_LIBRARY: `${API_CONFIG.API_BASE_PATH}/questions/from-library`,
  
  // Export endpoints
  EXPORT: `${API_CONFIG.API_BASE_PATH}/export/`,
  EXPORT_LIBRARY: `${API_CONFIG.API_BASE_PATH}/export/library`,
  EXPORT_EXAM: `${API_CONFIG.API_BASE_PATH}/export/exam`,
  EXPORT_EXAM_SUBSECTION: `${API_CONFIG.API_BASE_PATH}/export/exam-subsection`,
  EXPORT_EXAM_QUESTIONS_LIBRARY: `${API_CONFIG.API_BASE_PATH}/export/exam-questions-library`,
  EXPORT_EXAM_SECTION: `${API_CONFIG.API_BASE_PATH}/export/exam-section`,
  EXPORT_VIDEO_QUIZ: `${API_CONFIG.API_BASE_PATH}/export/video-quiz`,
};

// Helper function to get full API URL
export const getApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BACKEND_URL}${endpoint}`;
}; 