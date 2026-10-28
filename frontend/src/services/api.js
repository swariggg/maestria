const API_BASE = '/api/v1';

export async function apiRequest(endpoint, options = {}) {
  const defaultHeaders = {};
  if (!(options.body instanceof FormData)) {
    defaultHeaders['Content-Type'] = 'application/json';
  }

  // Token en localStorage si existe (para fallback oltre a Cookie)
  const token = localStorage.getItem('access_token');
  if (token) {
    defaultHeaders['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
    credentials: 'include', // Para enviar y recibir cookies HttpOnly
  };

  const response = await fetch(`${API_BASE}${endpoint}`, config);

  if (response.status === 401) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }

  if (!response.ok) {
    let errorDetail = 'Error en el servidor.';
    try {
      const errData = await response.json();
      errorDetail = errData.detail || errorDetail;
    } catch {
      // Ignorar si no es JSON
    }
    throw new Error(errorDetail);
  }

  // Si la respuesta es blob (por ejemplo descargas de PDF o Excel)
  const contentType = response.headers.get('content-type');
  if (contentType && (contentType.includes('pdf') || contentType.includes('spreadsheet') || contentType.includes('octet-stream'))) {
    return response.blob();
  }

  return response.json();
}

export const api = {
  // Auth
  login: (credentials) => apiRequest('/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  register: (data) => apiRequest('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  logout: () => apiRequest('/auth/logout', { method: 'POST' }),
  getMe: () => apiRequest('/auth/me'),

  // Dashboard
  getStats: () => apiRequest('/dashboard/stats'),

  // Programas y Convocatorias
  getPrograms: () => apiRequest('/programas'),
  createProgram: (data) => apiRequest('/programas', { method: 'POST', body: JSON.stringify(data) }),
  getConvocatorias: (progId) => apiRequest(`/programas/${progId}/convocatorias`),
  createConvocatoria: (data) => apiRequest('/programas/convocatorias', { method: 'POST', body: JSON.stringify(data) }),
  updateConvocatoria: (id, data) => apiRequest(`/programas/convocatorias/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  changeConvocatoriaEstado: (id, estado) => apiRequest(`/programas/convocatorias/${id}/estado`, { method: 'PATCH', body: JSON.stringify({ estado }) }),

  // Cursos y Actividades
  getCourses: (convId) => apiRequest(`/cursos${convId ? `?convocatoria_id=${convId}` : ''}`),
  createCourse: (data) => apiRequest('/cursos', { method: 'POST', body: JSON.stringify(data) }),
  getActivities: (cursoId) => apiRequest(`/cursos/${cursoId}/actividades`),
  createActivity: (data) => apiRequest('/cursos/actividades', { method: 'POST', body: JSON.stringify(data) }),

  // Postulantes
  getApplicants: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.search) params.append('search', filters.search);
    if (filters.programa_id) params.append('programa_id', filters.programa_id);
    if (filters.nivel_riesgo) params.append('nivel_riesgo', filters.nivel_riesgo);
    if (filters.estado_proceso) params.append('estado_proceso', filters.estado_proceso);
    return apiRequest(`/postulantes?${params.toString()}`);
  },

  // Inscripciones
  getOpenCalls: () => apiRequest('/inscripciones/convocatorias-abiertas'),
  getMyEnrollments: () => apiRequest('/inscripciones/mias'),
  enroll: (data) => apiRequest('/inscripciones', { method: 'POST', body: JSON.stringify(data) }),

  // Evidencias
  getEvidence: (actividadId, inscripcionId) => apiRequest(`/evidencias/actividad/${actividadId}/entrega?inscripcion_id=${inscripcionId}`),
  uploadEvidence: (formData) => apiRequest('/evidencias/upload', { method: 'POST', body: formData }),
  downloadEvidence: (versionId) => apiRequest(`/evidencias/version/${versionId}/download`),

  // Evaluaciones
  evaluateVersion: (data) => apiRequest('/evaluaciones', { method: 'POST', body: JSON.stringify(data) }),

  // Tutores
  getTutors: () => apiRequest('/tutores'),
  assignTutor: (data) => apiRequest('/tutores/asignar', { method: 'POST', body: JSON.stringify(data) }),

  // Seguimientos
  getFollowups: (inscripcionId) => apiRequest(`/seguimientos/inscripcion/${inscripcionId}`),
  createFollowup: (data) => apiRequest('/seguimientos', { method: 'POST', body: JSON.stringify(data) }),

  // Riesgos
  getRiskAlerts: () => apiRequest('/riesgos/alertas'),
  triggerRiskEvaluation: () => apiRequest('/riesgos/evaluar', { method: 'POST' }),
  resolveRiskAlert: (id, accion) => apiRequest(`/riesgos/alertas/${id}/resolver?accion_tomada=${encodeURIComponent(accion)}`, { method: 'POST' }),

  // Reportes
  downloadIndividualPdf: (inscripcionId) => apiRequest(`/reportes/individual/${inscripcionId}/pdf`),
  downloadConsolidatedExcel: (progId) => apiRequest(`/reportes/matriz/excel${progId ? `?programa_id=${progId}` : ''}`),

  // Auditoria
  getAuditLogs: (limit = 50) => apiRequest(`/auditoria?limit=${limit}`)
};
