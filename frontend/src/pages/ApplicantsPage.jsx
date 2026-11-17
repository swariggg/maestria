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
  AlertCircle,
  FileCheck,
  FolderOpen,
  History,
  Paperclip,
  CheckSquare,
  ClipboardCheck
} from 'lucide-react';
import { api } from '../services/api';
import Badge from '../components/Badge';
import Modal from '../components/Modal';
import DocumentsPanel from '../components/DocumentsPanel';
import HistoryTimeline from '../components/HistoryTimeline';
import { saveBlob } from '../utils/download';

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
  const [docsApplicant, setDocsApplicant] = useState(null);

  // Tutores
  const [tutors, setTutors] = useState([]);
  const [selectedTutorId, setSelectedTutorId] = useState('');
  const [assignError, setAssignError] = useState(null);
  const [assignMotivo, setAssignMotivo] = useState('');

  // Datos administrativos y retiro
  const [adminApplicant, setAdminApplicant] = useState(null);
  const [adminForm, setAdminForm] = useState(null);
  const [adminMsg, setAdminMsg] = useState(null);
  const [retiroObs, setRetiroObs] = useState('');

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
  const [observaciones, setObservaciones] = useState('');
  const [recomendaciones, setRecomendaciones] = useState('');
  const [compDesc, setCompDesc] = useState('');
  const [compDate, setCompDate] = useState('');
  const [evidFile, setEvidFile] = useState(null);
  const [estadoCaso, setEstadoCaso] = useState('EN_PROCESO');
  const [savingFollowup, setSavingFollowup] = useState(false);

  // Historial cronológico
  const [historyApplicant, setHistoryApplicant] = useState(null);
  const [history, setHistory] = useState(null);

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
    setAssignMotivo('');
    setSelectedTutorId('');
    try {
      // Solo los tutores que trabajan en el programa del postulante
      const tutorList = await api.getTutors(applicant.programa_id);
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
        tutor_id: parseInt(selectedTutorId),
        motivo: assignMotivo || null
      });
      setShowAssignModal(false);
      loadApplicants();
    } catch (err) {
      setAssignError(err.message);
    }
  };

  const handleOpenAdmin = (app) => {
    setAdminApplicant(app);
    setAdminMsg(null);
    setRetiroObs('');
    setAdminForm({
      estado_pago: app.estado_pago || 'PENDIENTE',
      tiene_beca: !!app.tiene_beca,
      porcentaje_beca: app.porcentaje_beca || '',
      requiere_adaptaciones: !!app.requiere_adaptaciones,
      nota_adaptaciones: app.nota_adaptaciones || '',
    });
  };

  const handleSaveAdmin = async (e) => {
    e.preventDefault();
    setAdminMsg(null);
    try {
      await api.updateAdministrative(adminApplicant.id, {
        ...adminForm,
        porcentaje_beca: adminForm.tiene_beca && adminForm.porcentaje_beca ? Number(adminForm.porcentaje_beca) : null,
        nota_adaptaciones: adminForm.requiere_adaptaciones ? adminForm.nota_adaptaciones || null : null,
      });
      setAdminMsg({ type: 'success', text: 'Datos guardados.' });
      loadApplicants();
    } catch (err) {
      setAdminMsg({ type: 'error', text: err.message });
    }
  };

  const handleRetiro = async (aprobar) => {
    setAdminMsg(null);
    try {
      const res = await api.resolveWithdrawal(adminApplicant.id, aprobar, retiroObs || null);
      setAdminMsg({ type: 'success', text: res.estado_proceso === 'RETIRADO' ? 'El postulante quedó retirado.' : 'Solicitud de retiro rechazada.' });
      setAdminApplicant({ ...adminApplicant, estado_proceso: res.estado_proceso, retiro_solicitado: false });
      loadApplicants();
    } catch (err) {
      setAdminMsg({ type: 'error', text: err.message });
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
    setObservaciones('');
    setRecomendaciones('');
    setCompDesc('');
    setCompDate('');
    setEvidFile(null);
    setEstadoCaso('EN_PROCESO');

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
    setFollowupError(null);
    if (['VIDEOCONFERENCIA', 'PRESENCIAL'].includes(contactType) && !evidFile) {
      setFollowupError('Para una videoconferencia o reunión presencial adjunte una evidencia (captura, acta o lista de asistencia).');
      return;
    }
    if ((compDesc && !compDate) || (!compDesc && compDate)) {
      setFollowupError('Para registrar un compromiso indique la descripción y la fecha.');
      return;
    }
    setSavingFollowup(true);
    try {
      const creado = await api.createFollowup({
        inscripcion_id: selectedApplicant.id,
        fecha_contacto: new Date().toISOString(),
        tipo_contacto: contactType,
        motivo: contactReason,
        accion_realizada: contactAction,
        resultado: contactResult,
        respuesta_postulante: huboRespuesta ? (applicantReply || null) : null,
        hubo_respuesta: huboRespuesta,
        proxima_accion: nextAction || null,
        fecha_proxima_accion: nextDate ? `${nextDate}T09:00:00` : null,
        estado_caso: estadoCaso,
        observaciones: observaciones || null,
        recomendaciones: recomendaciones || null,
        compromisos: compDesc ? [{ descripcion: compDesc, fecha_compromiso: compDate }] : []
      });

      if (evidFile) {
        const fd = new FormData();
        fd.append('file', evidFile);
        await api.uploadFollowupEvidence(creado.id, fd);
      }

      setFollowups(await api.getFollowups(selectedApplicant.id));
      loadApplicants();

      setContactReason('');
      setContactAction('');
      setContactResult('');
      setApplicantReply('');
      setNextAction('');
      setNextDate('');
      setObservaciones('');
      setRecomendaciones('');
      setCompDesc('');
      setCompDate('');
      setEvidFile(null);
    } catch (err) {
      setFollowupError(err.message);
    } finally {
      setSavingFollowup(false);
    }
  };

  const handleCommitmentDone = async (compromisoId) => {
    try {
      await api.markCommitmentDone(compromisoId);
      setFollowups(await api.getFollowups(selectedApplicant.id));
    } catch (err) {
      setFollowupError(err.message);
    }
  };

  const handleFollowupEvidence = async (seguimiento) => {
    try {
      saveBlob(await api.downloadFollowupEvidence(seguimiento.id), seguimiento.evidencia_nombre);
    } catch (err) {
      setFollowupError(err.message);
    }
  };

  const handleOpenHistory = async (app) => {
    setHistoryApplicant(app);
    setHistory(null);
    try {
      setHistory(await api.getEnrollmentHistory(app.id));
    } catch (err) {
      setHistory({ error: err.message });
    }
  };

  // Coordinación confirma que el postulante entregó los documentos obligatorios
  const handleDocumentationComplete = async (app) => {
    if (!window.confirm(`¿Confirmar que ${app.nombre_completo} entregó toda la documentación obligatoria?`)) return;
    try {
      await api.markDocumentationComplete(app.id);
      loadApplicants();
    } catch (err) {
      alert(`No se pudo actualizar: ${err.message}`);
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
              <option value="NO_APROBADO">No aprobado</option>
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
                      {app.requiere_adaptaciones && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--color-navy)', marginTop: '2px' }}>
                          Adaptaciones: {app.nota_adaptaciones || 'sí'}
                        </div>
                      )}
                    </td>
                    <td>
                      <div style={{ fontWeight: 500 }}>{app.programa_codigo}</div>
                      <small style={{ color: 'var(--text-sec)' }}>{app.convocatoria_nombre}</small>
                    </td>
                    <td style={{ minWidth: '110px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ flex: 1, height: '8px', background: 'var(--border-light)', borderRadius: '4px', overflow: 'hidden' }}>
                          <div style={{ width: `${app.porcentaje_avance}%`, height: '100%', background: 'var(--color-navy)' }}></div>
                        </div>
                        <small style={{ fontWeight: 600 }}>{app.porcentaje_avance}%</small>
                      </div>
                    </td>
                    <td>
                      {app.tutor_nombre ? (
                        <span>{app.tutor_nombre}</span>
                      ) : (
                        <span style={{ color: 'var(--status-warning-text)', fontStyle: 'italic' }}>Sin Tutor</span>
                      )}
                    </td>
                    <td>
                      <Badge type={app.estado_proceso} />
                      {app.retiro_solicitado && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--status-warning-text)', marginTop: '4px' }}>Pidió retirarse</div>
                      )}
                    </td>
                    <td>
                      <Badge type={app.nivel_riesgo} />
                      {app.motivo_riesgo && app.nivel_riesgo !== 'BAJO' && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--status-danger-text)', marginTop: '4px', maxWidth: '180px' }}>
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

                        {['ADMIN', 'COORDINADOR'].includes(role) && (
                          <button
                            className={app.retiro_solicitado ? 'btn btn-secondary' : 'btn btn-outline'}
                            style={{ padding: '6px 8px', fontSize: '0.8rem' }}
                            title="Pago, beca, adaptaciones y retiro"
                            onClick={() => handleOpenAdmin(app)}
                          >
                            <ClipboardCheck size={15} />
                          </button>
                        )}

                        {['ADMIN', 'COORDINADOR'].includes(role) && app.estado_proceso === 'DOCUMENTACION_PENDIENTE' && (
                          <button
                            className="btn btn-outline"
                            style={{ padding: '6px 8px', fontSize: '0.8rem' }}
                            title="Marcar documentación completa"
                            onClick={() => handleDocumentationComplete(app)}
                          >
                            <FileCheck size={15} />
                          </button>
                        )}

                        <button
                          className="btn btn-outline"
                          style={{ padding: '6px 8px', fontSize: '0.8rem' }}
                          title="Documentos del postulante"
                          onClick={() => setDocsApplicant(app)}
                        >
                          <FolderOpen size={15} />
                        </button>

                        <button
                          className="btn btn-secondary"
                          style={{ padding: '6px 8px', fontSize: '0.8rem' }}
                          title="Bitácora de Contacto y Seguimientos"
                          onClick={() => handleOpenFollowup(app)}
                        >
                          <MessageSquare size={15} />
                        </button>

                        <button
                          className="btn btn-outline"
                          style={{ padding: '6px 8px', fontSize: '0.8rem' }}
                          title="Historial cronológico"
                          onClick={() => handleOpenHistory(app)}
                        >
                          <History size={15} />
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
          <div style={{ background: 'var(--status-danger-bg)', color: 'var(--status-danger-text)', padding: '10px', borderRadius: '8px', marginBottom: '14px', fontSize: '0.875rem' }}>
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
                <option key={t.usuario_id} value={t.usuario_id} disabled={t.disponible === false}>
                  {t.nombre_completo} ({t.especialidad}) · {t.postulantes_asignados} de {t.max_postulantes} postulantes
                  {t.disponible === false ? (t.activo ? ' · sin cupo' : ' · inactivo') : ''}
                </option>
              ))}
            </select>
          </div>

          {tutors.length === 0 && (
            <small style={{ display: 'block', color: 'var(--status-warning-text)' }}>
              Ningún tutor trabaja en este programa. El administrador puede agregarlo en Usuarios.
            </small>
          )}
          {selectedApplicant?.tutor_id && (
            <div className="form-group">
              <label className="form-label">Motivo del cambio de tutor *</label>
              <input className="form-input" value={assignMotivo} onChange={(e) => setAssignMotivo(e.target.value)} minLength={5} required />
            </div>
          )}

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

      {/* Modal: Documentos del postulante */}
      <Modal
        isOpen={!!docsApplicant}
        onClose={() => setDocsApplicant(null)}
        wide
        title={`Documentos - ${docsApplicant?.nombre_completo || ''}`}
      >
        {docsApplicant && (
          <DocumentsPanel inscripcionId={docsApplicant.id} modo="revision" onChange={loadApplicants} puedeRevisar={role !== 'TUTOR'} />
        )}
      </Modal>

      {/* Modal: Pago, beca, adaptaciones y retiro */}
      <Modal
        isOpen={!!adminApplicant}
        onClose={() => setAdminApplicant(null)}
        title={`Datos administrativos - ${adminApplicant?.nombre_completo || ''}`}
      >
        {adminMsg && (
          <div className={adminMsg.type === 'error' ? 'notice-danger' : 'notice-success'} style={{ marginBottom: '14px' }}>{adminMsg.text}</div>
        )}
        {adminForm && (
          <form onSubmit={handleSaveAdmin}>
            <div className="form-group">
              <label className="form-label">Estado del pago</label>
              <select className="form-select" value={adminForm.estado_pago} onChange={(e) => setAdminForm({ ...adminForm, estado_pago: e.target.value })}>
                <option value="PENDIENTE">Pendiente</option>
                <option value="PAGADO">Pagado</option>
                <option value="EXONERADO">Exonerado</option>
              </select>
            </div>
            <label style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: '0.875rem', marginBottom: '10px' }}>
              <input type="checkbox" checked={adminForm.tiene_beca} onChange={(e) => setAdminForm({ ...adminForm, tiene_beca: e.target.checked })} />
              Tiene beca o descuento
            </label>
            {adminForm.tiene_beca && (
              <div className="form-group">
                <label className="form-label">Porcentaje de la beca</label>
                <input type="number" min="1" max="100" className="form-input" value={adminForm.porcentaje_beca}
                  onChange={(e) => setAdminForm({ ...adminForm, porcentaje_beca: e.target.value })} />
              </div>
            )}
            <label style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: '0.875rem', marginBottom: '10px' }}>
              <input type="checkbox" checked={adminForm.requiere_adaptaciones} onChange={(e) => setAdminForm({ ...adminForm, requiere_adaptaciones: e.target.checked })} />
              Necesita adaptaciones (discapacidad u otra condición)
            </label>
            {adminForm.requiere_adaptaciones && (
              <div className="form-group">
                <label className="form-label">Qué adaptaciones (visible para su tutor)</label>
                <input className="form-input" value={adminForm.nota_adaptaciones}
                  onChange={(e) => setAdminForm({ ...adminForm, nota_adaptaciones: e.target.value })} />
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button type="submit" className="btn btn-primary">Guardar</button>
            </div>
          </form>
        )}

        {adminApplicant && !['APROBADO', 'NO_APROBADO', 'RETIRADO'].includes(adminApplicant.estado_proceso) && (
          <div style={{ borderTop: '1px solid var(--border-light)', marginTop: '18px', paddingTop: '14px' }}>
            <h4 style={{ marginBottom: '8px' }}>Retiro</h4>
            {adminApplicant.retiro_solicitado ? (
              <p style={{ fontSize: '0.875rem', marginBottom: '10px' }}>
                El postulante pidió retirarse: <em>{adminApplicant.motivo_retiro}</em>
              </p>
            ) : (
              <p style={{ fontSize: '0.875rem', color: 'var(--text-sec)', marginBottom: '10px' }}>
                No hay solicitud. Puede retirarlo directamente indicando el motivo (por ejemplo, si lo pidió por otro medio).
              </p>
            )}
            <input className="form-input" placeholder="Observación (se envía al postulante)" value={retiroObs} onChange={(e) => setRetiroObs(e.target.value)} />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '10px' }}>
              {adminApplicant.retiro_solicitado && (
                <button type="button" className="btn btn-outline" onClick={() => handleRetiro(false)}>Rechazar solicitud</button>
              )}
              <button type="button" className="btn btn-secondary" onClick={() => handleRetiro(true)}
                disabled={!adminApplicant.retiro_solicitado && retiroObs.trim().length < 5}>
                {adminApplicant.retiro_solicitado ? 'Aprobar retiro' : 'Retirar postulante'}
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Modal: Historial cronológico */}
      <Modal
        isOpen={!!historyApplicant}
        onClose={() => setHistoryApplicant(null)}
        title={`Historial - ${historyApplicant?.nombre_completo || ''}`}
        wide
      >
        {!history ? (
          <div style={{ padding: '20px', textAlign: 'center' }}>Cargando historial...</div>
        ) : history.error ? (
          <div className="notice-danger">{history.error}</div>
        ) : (
          <HistoryTimeline eventos={history} />
        )}
      </Modal>

      {/* Modal: Seguimientos y Bitácora */}
      <Modal
        isOpen={showFollowupModal}
        onClose={() => setShowFollowupModal(false)}
        title={`Bitácora de Seguimientos - ${selectedApplicant?.nombre_completo}`}
        wide
      >
        {followupError && <div className="notice-danger" style={{ marginBottom: '14px' }}>{followupError}</div>}

        {/* Seguimientos registrados */}
        <div style={{ maxHeight: '260px', overflowY: 'auto', marginBottom: '20px', borderBottom: '1px solid var(--border-light)', paddingBottom: '12px' }}>
          <h4 style={{ fontSize: '0.95rem', marginBottom: '10px', color: 'var(--text-sec)' }}>Seguimientos registrados ({followups.length})</h4>
          {followups.length === 0 ? (
            <p style={{ color: 'var(--text-sec)', fontSize: '0.875rem' }}>No existen contactos registrados previamente.</p>
          ) : (
            followups.map((s) => (
              <div key={s.id} style={{ background: 'var(--surface-muted)', padding: '10px 14px', borderRadius: '10px', marginBottom: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <strong>#{s.numero_seguimiento} · {s.tipo_contacto} · {s.motivo}</strong>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Badge type={s.estado_caso} />
                    <small style={{ color: 'var(--text-sec)' }}>{new Date(s.fecha_contacto).toLocaleDateString()}</small>
                  </div>
                </div>
                <p style={{ fontSize: '0.85rem', margin: '4px 0' }}><strong>Acción:</strong> {s.accion_realizada}</p>
                {s.resultado && <p style={{ fontSize: '0.85rem', margin: '4px 0' }}><strong>Resultado:</strong> {s.resultado}</p>}
                {s.observaciones && <p style={{ fontSize: '0.85rem', margin: '4px 0' }}><strong>Observaciones:</strong> {s.observaciones}</p>}
                {s.recomendaciones && <p style={{ fontSize: '0.85rem', margin: '4px 0' }}><strong>Recomendaciones:</strong> {s.recomendaciones}</p>}
                {s.compromisos.map((c) => (
                  <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', margin: '4px 0' }}>
                    <CheckSquare size={14} color={c.cumplido ? 'var(--status-success-text)' : 'var(--text-sec)'} />
                    <span style={{ textDecoration: c.cumplido ? 'line-through' : 'none' }}>
                      Compromiso: {c.descripcion} (hasta {new Date(`${c.fecha_compromiso}T00:00:00`).toLocaleDateString()})
                    </span>
                    {!c.cumplido && (
                      <button type="button" className="btn btn-outline" style={{ padding: '2px 8px', fontSize: '0.75rem' }} onClick={() => handleCommitmentDone(c.id)}>
                        Marcar cumplido
                      </button>
                    )}
                  </div>
                ))}
                <div style={{ display: 'flex', gap: '10px', fontSize: '0.8rem', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span>Respuesta: <strong>{s.hubo_respuesta ? (s.respuesta_postulante || 'Sí respondió') : 'SIN RESPUESTA'}</strong></span>
                  <span>•</span>
                  <span>Por: {s.tutor_nombre}</span>
                  {s.proxima_accion && (<><span>•</span><span>Próxima acción: {s.proxima_accion}</span></>)}
                  {s.evidencia_nombre && (
                    <button type="button" className="btn btn-outline" style={{ padding: '2px 8px', fontSize: '0.75rem' }} onClick={() => handleFollowupEvidence(s)}>
                      <Paperclip size={12} />
                      <span>{s.evidencia_nombre}</span>
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Formulario nuevo contacto */}
        <form onSubmit={handleSaveFollowup}>
          <h4 style={{ fontSize: '0.95rem', marginBottom: '10px' }}>Registrar nuevo contacto (#{followups.length + 1})</h4>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0 12px' }}>
            <div className="form-group">
              <label className="form-label">Medio de contacto</label>
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
                  <span style={{ color: 'var(--status-danger-text)', fontWeight: 600 }}>Sin respuesta</span>
                </label>
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Estado del caso</label>
              <select className="form-select" value={estadoCaso} onChange={(e) => setEstadoCaso(e.target.value)}>
                <option value="ABIERTO">Abierto</option>
                <option value="EN_PROCESO">En proceso</option>
                <option value="RESUELTO">Resuelto</option>
                <option value="ESCALADO">Escalado a coordinación</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Motivo</label>
            <input type="text" className="form-input" placeholder="Ej. Revisión de dudas en Taller 2..." value={contactReason} onChange={(e) => setContactReason(e.target.value)} required />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0 12px' }}>
            <div className="form-group">
              <label className="form-label">Acción realizada</label>
              <textarea className="form-textarea" rows={2} placeholder="Qué se hizo en el contacto" value={contactAction} onChange={(e) => setContactAction(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">Resultado</label>
              <textarea className="form-textarea" rows={2} placeholder="Qué se logró o acordó" value={contactResult} onChange={(e) => setContactResult(e.target.value)} required />
            </div>
            {huboRespuesta && (
              <div className="form-group">
                <label className="form-label">Respuesta del postulante</label>
                <textarea className="form-textarea" rows={2} value={applicantReply} onChange={(e) => setApplicantReply(e.target.value)} />
              </div>
            )}
            <div className="form-group">
              <label className="form-label">Observaciones</label>
              <textarea className="form-textarea" rows={2} value={observaciones} onChange={(e) => setObservaciones(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Recomendaciones</label>
              <textarea className="form-textarea" rows={2} value={recomendaciones} onChange={(e) => setRecomendaciones(e.target.value)} />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label className="form-label">Compromiso adquirido (opcional)</label>
              <input className="form-input" placeholder="Ej. Entregar el Taller 2 corregido" value={compDesc} onChange={(e) => setCompDesc(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Fecha del compromiso</label>
              <input type="date" className="form-input" value={compDate} onChange={(e) => setCompDate(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Próxima acción</label>
              <input className="form-input" placeholder="Ej. Llamar el lunes" value={nextAction} onChange={(e) => setNextAction(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Fecha</label>
              <input type="date" className="form-input" value={nextDate} onChange={(e) => setNextDate(e.target.value)} />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Evidencia del contacto {['VIDEOCONFERENCIA', 'PRESENCIAL'].includes(contactType) ? '* (obligatoria para videoconferencia o presencial)' : '(opcional: captura, acta, correo)'}</label>
            <input type="file" className="form-input" accept=".pdf,.jpg,.jpeg,.png,.docx,.txt" onChange={(e) => setEvidFile(e.target.files[0] || null)} />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '16px' }}>
            <button type="button" className="btn btn-outline" onClick={() => setShowFollowupModal(false)}>
              Cerrar
            </button>
            <button type="submit" className="btn btn-primary" disabled={savingFollowup}>
              {savingFollowup ? 'Guardando...' : 'Guardar Seguimiento'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
