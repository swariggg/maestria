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

  // En el login un 401 es solo una contraseña equivocada: se muestra el mensaje, sin recargar
  if (response.status === 401 && endpoint !== '/auth/login') {
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
  if (contentType && !contentType.includes('application/json')) {
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
  changeInitialPassword: (data) => apiRequest('/auth/cambiar-password', { method: 'POST', body: JSON.stringify(data) }),

  // Dashboard
  getStats: () => apiRequest('/dashboard/stats'),

  // Programas y Convocatorias
  getPrograms: () => apiRequest('/programas'),
  createProgram: (data) => apiRequest('/programas', { method: 'POST', body: JSON.stringify(data) }),
  getConvocatorias: (progId) => apiRequest(`/programas/${progId}/convocatorias`),
  createConvocatoria: (data) => apiRequest('/programas/convocatorias', { method: 'POST', body: JSON.stringify(data) }),
  updateConvocatoria: (id, data) => apiRequest(`/programas/convocatorias/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  changeConvocatoriaEstado: (id, estado, motivo) => apiRequest(`/programas/convocatorias/${id}/estado`, { method: 'PATCH', body: JSON.stringify({ estado, motivo }) }),

  // Cursos y Actividades
  getCourses: (convId) => apiRequest(`/cursos${convId ? `?convocatoria_id=${convId}` : ''}`),
  createCourse: (data) => apiRequest('/cursos', { method: 'POST', body: JSON.stringify(data) }),
  getActivities: (cursoId) => apiRequest(`/cursos/${cursoId}/actividades`),
  createActivity: (data) => apiRequest('/cursos/actividades', { method: 'POST', body: JSON.stringify(data) }),
  getTemplates: (programaId) => apiRequest(`/cursos/plantillas?programa_id=${programaId}`),
  createTemplate: (data) => apiRequest('/cursos/plantillas', { method: 'POST', body: JSON.stringify(data) }),
  deleteTemplate: (id) => apiRequest(`/cursos/plantillas/${id}`, { method: 'DELETE' }),
  updateCourse: (id, data) => apiRequest(`/cursos/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  setCourseTutor: (id, data) => apiRequest(`/cursos/${id}/tutor`, { method: 'PUT', body: JSON.stringify(data) }),
  updateActivity: (id, data) => apiRequest(`/cursos/actividades/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteActivity: (id) => apiRequest(`/cursos/actividades/${id}`, { method: 'DELETE' }),
  getCriteria: (actividadId) => apiRequest(`/cursos/actividades/${actividadId}/criterios`),
  setCriteria: (actividadId, criterios) => apiRequest(`/cursos/actividades/${actividadId}/criterios`, { method: 'PUT', body: JSON.stringify({ criterios }) }),

  // Materiales del curso (archivos, enlaces y sesiones)
  getMaterials: (cursoId) => apiRequest(`/materiales/curso/${cursoId}`),
  createMaterial: (formData) => apiRequest('/materiales', { method: 'POST', body: formData }),
  deleteMaterial: (id) => apiRequest(`/materiales/${id}`, { method: 'DELETE' }),
  downloadMaterial: (id) => apiRequest(`/materiales/${id}/download`),

  // Perfil y documentos del postulante
  getNotifications: () => apiRequest('/notificaciones'),
  markNotificationRead: (id) => apiRequest(`/notificaciones/${id}/leida`, { method: 'PATCH' }),
  markAllNotificationsRead: () => apiRequest('/notificaciones/leer-todas', { method: 'POST' }),
  getMyProfile: () => apiRequest('/perfil'),
  updateMyProfile: (data) => apiRequest('/perfil', { method: 'PUT', body: JSON.stringify(data) }),
  getRequirements: (convId) => apiRequest(`/documentos/requisitos?convocatoria_id=${convId}`),
  createRequirement: (data) => apiRequest('/documentos/requisitos', { method: 'POST', body: JSON.stringify(data) }),
  updateRequirement: (id, data) => apiRequest(`/documentos/requisitos/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteRequirement: (id) => apiRequest(`/documentos/requisitos/${id}`, { method: 'DELETE' }),
  getEnrollmentDocuments: (inscripcionId) => apiRequest(`/documentos/inscripcion/${inscripcionId}`),
  uploadDocument: (formData) => apiRequest('/documentos/upload', { method: 'POST', body: formData }),
  reviewDocument: (id, data) => apiRequest(`/documentos/${id}/revision`, { method: 'PATCH', body: JSON.stringify(data) }),
  reopenDocument: (id, motivo) => apiRequest(`/documentos/${id}/reabrir`, { method: 'PATCH', body: JSON.stringify({ motivo }) }),
  downloadDocument: (id) => apiRequest(`/documentos/${id}/download`),

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
  getCertificates: (inscripcionId) => apiRequest(`/certificados/inscripcion/${inscripcionId}`),
  getPendingCertificates: () => apiRequest('/certificados/pendientes'),
  downloadCourseCertificate: (asignacionId) => apiRequest(`/certificados/${asignacionId}/pdf`),
  reviewCertificate: (asignacionId, data) => apiRequest(`/certificados/${asignacionId}/revision`, { method: 'PATCH', body: JSON.stringify(data) }),
  enroll: (data) => apiRequest('/inscripciones', { method: 'POST', body: JSON.stringify(data) }),
  getEnrollmentProgress: (inscripcionId) => apiRequest(`/inscripciones/${inscripcionId}/avance`),
  markDocumentationComplete: (inscripcionId) => apiRequest(`/inscripciones/${inscripcionId}/documentacion-completa`, { method: 'PATCH' }),
  requestWithdrawal: (inscripcionId, motivo) => apiRequest(`/inscripciones/${inscripcionId}/solicitar-retiro`, { method: 'POST', body: JSON.stringify({ motivo }) }),
  resolveWithdrawal: (inscripcionId, aprobar, observacion) => apiRequest(`/inscripciones/${inscripcionId}/retiro`, { method: 'PATCH', body: JSON.stringify({ aprobar, observacion }) }),
  updateAdministrative: (inscripcionId, data) => apiRequest(`/inscripciones/${inscripcionId}/administrativo`, { method: 'PUT', body: JSON.stringify(data) }),

  // Evidencias
  getEvidence: (actividadId, inscripcionId) => apiRequest(`/evidencias/actividad/${actividadId}/entrega?inscripcion_id=${inscripcionId}`),
  uploadEvidence: (formData) => apiRequest('/evidencias/upload', { method: 'POST', body: formData }),
  downloadEvidence: (versionId) => apiRequest(`/evidencias/version/${versionId}/download`),

  // Evaluaciones
  evaluateVersion: (data) => apiRequest('/evaluaciones', { method: 'POST', body: JSON.stringify(data) }),

  // Tutores
  getTutors: (programaId) => apiRequest(`/tutores${programaId ? `?programa_id=${programaId}` : ''}`),

  // Seguimientos
  getFollowups: (inscripcionId) => apiRequest(`/seguimientos/inscripcion/${inscripcionId}`),
  createFollowup: (data) => apiRequest('/seguimientos', { method: 'POST', body: JSON.stringify(data) }),
  uploadFollowupEvidence: (id, formData) => apiRequest(`/seguimientos/${id}/evidencia`, { method: 'POST', body: formData }),
  downloadFollowupEvidence: (id) => apiRequest(`/seguimientos/${id}/evidencia`),
  markCommitmentDone: (id) => apiRequest(`/seguimientos/compromisos/${id}/cumplido`, { method: 'PATCH' }),
  getEnrollmentHistory: (inscripcionId) => apiRequest(`/inscripciones/${inscripcionId}/historial`),

  // Riesgos
  getRiskAlerts: (incluirResueltas = false) => apiRequest(`/riesgos/alertas${incluirResueltas ? '?incluir_resueltas=true' : ''}`),
  triggerRiskEvaluation: () => apiRequest('/riesgos/evaluar', { method: 'POST' }),
  evaluateRisks: () => apiRequest('/riesgos/evaluar', { method: 'POST' }),
  getMyAlerts: () => apiRequest('/riesgos/mis-alertas'),
  getAlertRecipients: (id) => apiRequest(`/riesgos/alertas/${id}/destinatarios`),
  deriveAlert: (id, destinatario_id, nota) => apiRequest(`/riesgos/alertas/${id}/derivar`, { method: 'POST', body: JSON.stringify({ destinatario_id, nota }) }),
  resolveRiskAlert: (id, accion) => apiRequest(`/riesgos/alertas/${id}/resolver?accion_tomada=${encodeURIComponent(accion)}`, { method: 'POST' }),

  // Reportes
  downloadIndividualPdf: (inscripcionId) => apiRequest(`/reportes/individual/${inscripcionId}/pdf`),
  downloadCertificate: (inscripcionId) => apiRequest(`/reportes/certificado/${inscripcionId}`),
  downloadConsolidatedExcel: (progId) => apiRequest(`/reportes/matriz/excel${progId ? `?programa_id=${progId}` : ''}`),
  downloadConsolidatedPdf: (progId) => apiRequest(`/reportes/matriz/pdf${progId ? `?programa_id=${progId}` : ''}`),
  downloadTraceability: (formato, params = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== '')).toString();
    return apiRequest(`/reportes/trazabilidad/${formato}${qs ? `?${qs}` : ''}`);
  },

  // Configuración (solo administrador)
  getParameters: () => apiRequest('/configuracion'),
  updateParameters: (valores) => apiRequest('/configuracion', { method: 'PUT', body: JSON.stringify({ valores }) }),

  // Usuarios (solo administrador)
  getUsers: (rol) => apiRequest(`/usuarios${rol ? `?rol=${rol}` : ''}`),
  createUser: (data) => apiRequest('/usuarios', { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (id, data) => apiRequest(`/usuarios/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  setUserStatus: (id, estado) => apiRequest(`/usuarios/${id}/estado`, { method: 'PATCH', body: JSON.stringify({ estado }) }),
  resetUserPassword: (id, password) => apiRequest(`/usuarios/${id}/password`, { method: 'POST', body: JSON.stringify({ password }) }),
  setUserPrograms: (id, programaIds) => apiRequest(`/usuarios/${id}/programas`, { method: 'PUT', body: JSON.stringify({ programa_ids: programaIds }) }),

  // Auditoria
  getAuditLogs: (limit = 50) => apiRequest(`/auditoria?limit=${limit}`)
};
