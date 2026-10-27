import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Filter, 
  UserPlus, 
  MessageSquare, 
  FileDown, 
  PhoneCall, 
  Mail, 
  Calendar,
  AlertCircle
} from 'lucide-react';
import { api } from '../services/api';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

export default function ApplicantsPage({ user }) {
  const [applicants, setApplicants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Modales
  const [selectedApplicant, setSelectedApplicant] = useState(null);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [showFollowupModal, setShowFollowupModal] = useState(false);

  // Tutores
  const [tutors, setTutors] = useState([]);
  const [selectedTutorId, setSelectedTutorId] = useState('');
  const [assignError, setAssignError] = useState(null);

  // Seguimientos
  const [followups, setFollowups] = useState([]);
  const [contactType, setContactType] = useState('TELEFONO');
  const [contactReason, setContactReason] = useState('');
  const [contactAction, setContactAction] = useState('');
  const [contactResult, setContactResult] = useState('');
  const [applicantReply, setApplicantReply] = useState('');
  const [huboRespuesta, setHuboRespuesta] = useState(true);
  const [nextAction, setNextAction] = useState('');
  const [nextDate, setNextDate] = useState('');
  const [followupError, setFollowupError] = useState(null);

  const loadApplicants = async () => {
    try {
      setLoading(true);
      const data = await api.getApplicants({
        search: search || undefined,
        nivel_riesgo: riskFilter || undefined,
        estado_proceso: statusFilter || undefined
      });
      setApplicants(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApplicants();
  }, [riskFilter, statusFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadApplicants();
  };

  // Abrir Modal de Asignación de Tutor
  const handleOpenAssign = async (applicant) => {
    setSelectedApplicant(applicant);
    setAssignError(null);
    try {
      const tutorList = await api.getTutors();
      setTutors(tutorList);
      setShowAssignModal(true);
    } catch (err) {
      alert(`Error cargando tutores: ${err.message}`);
    }
  };

  const handleSaveAssignment = async (e) => {
    e.preventDefault();
    if (!selectedTutorId) return;
    try {
      await api.assignTutor({
        inscripcion_id: selectedApplicant.id,
        tutor_id: parseInt(selectedTutorId)
      });
      setShowAssignModal(false);
      loadApplicants();
    } catch (err) {
      setAssignError(err.message);
    }
  };

  // Abrir Modal de Seguimientos
  const handleOpenFollowup = async (applicant) => {
    setSelectedApplicant(applicant);
    setFollowupError(null);
    setContactReason('');
    setContactAction('');
    setContactResult('');
    setApplicantReply('');
    setHuboRespuesta(true);
    setNextAction('');
    setNextDate('');

    try {
      const data = await api.getFollowups(applicant.id);
      setFollowups(data);
      setShowFollowupModal(true);
    } catch (err) {
      alert(`Error cargando seguimientos: ${err.message}`);
    }
  };

  const handleSaveFollowup = async (e) => {
    e.preventDefault();
    try {
      await api.createFollowup({
        inscripcion_id: selectedApplicant.id,
        fecha_contacto: new Date().toISOString(),
        tipo_contacto: contactType,
        motivo: contactReason,
        accion_realizada: contactAction,
        resultado: contactResult,
        respuesta_postulante: applicantReply,
        hubo_respuesta: huboRespuesta,
        proxima_accion: nextAction || null,
        fecha_proxima_accion: nextDate ? new Date(nextDate).toISOString() : null,
        estado_caso: huboRespuesta ? 'RESUELTO' : 'EN_PROCESO'
      });

      // Recargar lista de seguimientos y postulantes
      const data = await api.getFollowups(selectedApplicant.id);
      setFollowups(data);
      loadApplicants();

      // Limpiar formulario
      setContactReason('');
      setContactAction('');
      setContactResult('');
      setApplicantReply('');
      alert('Seguimiento registrado exitosamente.');
    } catch (err) {
      setFollowupError(err.message);
    }
  };

  // Descargar PDF Individual
  const handleDownloadPdf = async (inscripcionId, cedula) => {
    try {
      const blob = await api.downloadIndividualPdf(inscripcionId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reporte_individual_${cedula}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      alert(`Error descargando PDF: ${err.message}`);
    }
  };

  const role = user?.rol?.codigo;

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1>Gestión y Seguimiento de Postulantes</h1>
        <p style={{ color: 'var(--text-sec)' }}>
          Supervisión de expedientes, asignación de tutores y registro cronológico de contactos.
        </p>
      </div>

      {/* Barra de Filtros */}
      <div className="card" style={{ marginBottom: '24px', padding: '18px 24px' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', flex: '1', minWidth: '220px' }}>
            <input
              type="text"
              className="form-input"
              style={{ paddingLeft: '36px' }}
              placeholder="Buscar por nombre o cédula..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Search size={18} color="var(--text-sec)" style={{ position: 'absolute', left: '10px', top: '11px' }} />
          </div>

          <div style={{ minWidth: '160px' }}>
            <select className="form-select" value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)}>
              <option value="">Riesgo (Todos)</option>
              <option value="BAJO">Riesgo Bajo</option>
              <option value="MEDIO">Riesgo Medio</option>
              <option value="ALTO">Riesgo Alto</option>
            </select>
          </div>

          <div style={{ minWidth: '180px' }}>
            <select className="form-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">Estado (Todos)</option>
              <option value="REGISTRADO">Registrado</option>
              <option value="DOCUMENTACION_PENDIENTE">Doc. Pendiente</option>
              <option value="EN_CURSO">En Curso</option>
              <option value="APROBADO">Aprobado</option>
              <option value="REPROBADO">Reprobado</option>
            </select>
          </div>

          <button type="submit" className="btn btn-primary">
            <Filter size={16} />
            <span>Filtrar</span>
          </button>
        </form>
      </div>

      {/* Tabla de Postulantes */}
      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center' }}>Cargando registros...</div>
        ) : applicants.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-sec)' }}>
            No se encontraron postulantes con los filtros seleccionados.
          </div>
        ) : (
          <div className="table-responsive" style={{ border: 'none' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Postulante</th>
                  <th>Programa / Convocatoria</th>
                  <th>Avance</th>
                  <th>Tutor Asignado</th>
                  <th>Estado</th>
                  <th>Nivel de Riesgo</th>
                  <th style={{ textAlign: 'center' }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {applicants.map((app) => (
                  <tr key={app.id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{app.nombre_completo}</div>
                      <small style={{ color: 'var(--text-sec)' }}>CI: {app.cedula} • {app.email}</small>
                    </td>
                    <td>
                      <div style={{ fontWeight: 500 }}>{app.programa_codigo}</div>
                      <small style={{ color: 'var(--text-sec)' }}>{app.convocatoria_nombre}</small>
                    </td>
                    <td style={{ minWidth: '110px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ flex: 1, height: '8px', background: '#E6E9F2', borderRadius: '4px', overflow: 'hidden' }}>
                          <div style={{ width: `${app.porcentaje_avance}%`, height: '100%', background: 'var(--color-primary-text)' }}></div>
                        </div>
                        <small style={{ fontWeight: 600 }}>{app.porcentaje_avance}%</small>
                      </div>
                    </td>
                    <td>
                      {app.tutor_nombre ? (
                        <span>{app.tutor_nombre}</span>
                      ) : (
                        <span style={{ color: '#D97706', fontStyle: 'italic' }}>Sin Tutor</span>
                      )}
                    </td>
                    <td>
                      <Badge type={app.estado_proceso} />
                    </td>
                    <td>
                      <Badge type={app.nivel_riesgo} />
                      {app.motivo_riesgo && app.nivel_riesgo !== 'BAJO' && (
                        <div style={{ fontSize: '0.75rem', color: '#DC2626', marginTop: '4px', maxWidth: '180px' }}>
                          {app.motivo_riesgo}
                        </div>
                      )}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <div style={{ display: 'inline-flex', gap: '6px' }}>
                        {['ADMIN', 'COORDINADOR'].includes(role) && (
                          <button
                            className="btn btn-outline"
                            style={{ padding: '6px 8px', fontSize: '0.8rem' }}
                            title="Asignar o Cambiar Tutor"
                            onClick={() => handleOpenAssign(app)}
                          >
                            <UserPlus size={15} />
                          </button>
                        )}

                        <button
                          className="btn btn-secondary"
                          style={{ padding: '6px 8px', fontSize: '0.8rem' }}
                          title="Bitácora de Contacto y Seguimientos"
                          onClick={() => handleOpenFollowup(app)}
                        >
                          <MessageSquare size={15} />
                        </button>

                        <button
                          className="btn btn-comp"
                          style={{ padding: '6px 8px', fontSize: '0.8rem' }}
                          title="Descargar Informe Individual en PDF"
                          onClick={() => handleDownloadPdf(app.id, app.cedula)}
                        >
                          <FileDown size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Asignar Tutor */}
      <Modal
        isOpen={showAssignModal}
        onClose={() => setShowAssignModal(false)}
        title={`Asignar Tutor - ${selectedApplicant?.nombre_completo}`}
      >
        {assignError && (
          <div style={{ background: '#FEE2E2', color: '#DC2626', padding: '10px', borderRadius: '8px', marginBottom: '14px', fontSize: '0.875rem' }}>
            {assignError}
          </div>
        )}
        <form onSubmit={handleSaveAssignment}>
          <div className="form-group">
            <label className="form-label">Seleccionar Tutor Académico</label>
            <select
              className="form-select"
              value={selectedTutorId}
              onChange={(e) => setSelectedTutorId(e.target.value)}
              required
            >
              <option value="">-- Elija un tutor --</option>
              {tutors.map((t) => (
                <option key={t.usuario_id} value={t.usuario_id}>
                  {t.nombre_completo} ({t.especialidad}) - [{t.postulantes_asignados}/{t.max_postulantes} postulantes]
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn btn-outline" onClick={() => setShowAssignModal(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary">
              Confirmar Asignación
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Seguimientos y Bitácora */}
      <Modal
        isOpen={showFollowupModal}
        onClose={() => setShowFollowupModal(false)}
        title={`Bitácora de Seguimientos - ${selectedApplicant?.nombre_completo}`}
      >
        {followupError && (
          <div style={{ background: '#FEE2E2', color: '#DC2626', padding: '10px', borderRadius: '8px', marginBottom: '14px', fontSize: '0.875rem' }}>
            {followupError}
          </div>
        )}

        {/* Historial previo */}
        <div style={{ maxHeight: '200px', overflowY: 'auto', marginBottom: '20px', borderBottom: '1px solid var(--border-light)', paddingBottom: '12px' }}>
          <h4 style={{ fontSize: '0.95rem', marginBottom: '10px', color: 'var(--text-sec)' }}>Historial Cronológico</h4>
          {followups.length === 0 ? (
            <p style={{ color: 'var(--text-sec)', fontSize: '0.875rem' }}>No existen contactos registrados previamente.</p>
          ) : (
            followups.map((s) => (
              <div key={s.id} style={{ background: 'var(--surface-muted)', padding: '10px 14px', borderRadius: '10px', marginBottom: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>{s.tipo_contacto} - {s.motivo}</strong>
                  <small style={{ color: 'var(--text-sec)' }}>{new Date(s.fecha_contacto).toLocaleDateString()}</small>
                </div>
                <p style={{ fontSize: '0.85rem', margin: '4px 0' }}>{s.accion_realizada}</p>
                <div style={{ display: 'flex', gap: '10px', fontSize: '0.8rem' }}>
                  <span>Respuesta: <strong>{s.hubo_respuesta ? (s.respuesta_postulante || 'Sí respondió') : 'SIN RESPUESTA'}</strong></span>
                  <span>•</span>
                  <span>Por: {s.tutor_nombre}</span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Formulario nuevo contacto */}
        <form onSubmit={handleSaveFollowup}>
          <h4 style={{ fontSize: '0.95rem', marginBottom: '10px' }}>Registrar Nuevo Contacto</h4>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label className="form-label">Medio de Contacto</label>
              <select className="form-select" value={contactType} onChange={(e) => setContactType(e.target.value)}>
                <option value="TELEFONO">Llamada Telefónica</option>
                <option value="CORREO">Correo Electrónico</option>
                <option value="WHATSAPP">WhatsApp</option>
                <option value="VIDEOCONFERENCIA">Videoconferencia</option>
                <option value="PRESENCIAL">Presencial</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">¿El postulante respondió?</label>
              <div style={{ display: 'flex', gap: '14px', alignItems: 'center', marginTop: '8px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                  <input type="radio" checked={huboRespuesta} onChange={() => setHuboRespuesta(true)} />
                  <span>Sí respondió</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                  <input type="radio" checked={!huboRespuesta} onChange={() => setHuboRespuesta(false)} />
                  <span style={{ color: '#DC2626', fontWeight: 600 }}>Sin respuesta</span>
                </label>
              </div>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Motivo</label>
            <input
              type="text"
              className="form-input"
              placeholder="Ej. Revisión de dudas en Taller 2..."
              value={contactReason}
              onChange={(e) => setContactReason(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Acción y Resultado</label>
            <textarea
              className="form-textarea"
              rows={2}
              placeholder="Describa la intervención y el resultado acordado..."
              value={contactAction}
              onChange={(e) => setContactAction(e.target.value)}
              required
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '16px' }}>
            <button type="button" className="btn btn-outline" onClick={() => setShowFollowupModal(false)}>
              Cerrar
            </button>
            <button type="submit" className="btn btn-primary">
              Guardar Seguimiento
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
