import React, { useState, useEffect } from 'react';
import { 
  Upload, 
  Download, 
  CheckCircle, 
  FileText, 
  MessageSquare, 
  Clock, 
  AlertCircle 
} from 'lucide-react';
import { api } from '../services/api';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

export default function EvidencesPage({ user }) {
  const [courses, setCourses] = useState([]);
  const [activities, setActivities] = useState([]);
  const [selectedAct, setSelectedAct] = useState(null);
  const [applicants, setApplicants] = useState([]);
  const [selectedInscId, setSelectedInscId] = useState(null);
  const [evidenceData, setEvidenceData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Modal Subida (Postulante)
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Modal Evaluación (Tutor/Coord)
  const [showEvalModal, setShowEvalModal] = useState(false);
  const [evalVersionId, setEvalVersionId] = useState(null);
  const [evalScore, setEvalScore] = useState('');
  const [evalResult, setEvalResult] = useState('APROBADO');
  const [evalObs, setEvalObs] = useState('');
  const [evalRec, setEvalRec] = useState('');
  const [evalError, setEvalError] = useState(null);

  const role = user?.rol?.codigo;

  const loadInitial = async () => {
    try {
      setLoading(true);
      const crsList = await api.getCourses();
      setCourses(crsList);

      if (crsList.length > 0) {
        const actList = await api.getActivities(crsList[0].id);
        setActivities(actList);
        if (actList.length > 0) setSelectedAct(actList[0]);
      }

      if (['ADMIN', 'COORDINADOR', 'TUTOR'].includes(role)) {
        const appList = await api.getApplicants();
        setApplicants(appList);
        if (appList.length > 0) {
          setSelectedInscId(appList[0].id);
        }
      } else {
        // Postulante
        const appList = await api.getApplicants();
        if (appList.length > 0) {
          setSelectedInscId(appList[0].id);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitial();
  }, []);

  const loadEvidence = async (actId, inscId) => {
    if (!actId || !inscId) return;
    try {
      const data = await api.getEvidence(actId, inscId);
      setEvidenceData(data);
    } catch (err) {
      console.error(err);
      setEvidenceData(null);
    }
  };

  useEffect(() => {
    if (selectedAct && selectedInscId) {
      loadEvidence(selectedAct.id, selectedInscId);
    }
  }, [selectedAct, selectedInscId]);

  // Manejar Subida de Evidencia
  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;
    setUploadError(null);
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('actividad_id', selectedAct.id);
      formData.append('inscripcion_id', selectedInscId);
      formData.append('file', uploadFile);

      await api.uploadEvidence(formData);
      setShowUploadModal(false);
      setUploadFile(null);
      await loadEvidence(selectedAct.id, selectedInscId);
      alert('Evidencia cargada exitosamente al repositorio privado.');
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  };

  // Descarga Segura de Archivo
  const handleDownloadFile = async (versionId, originalName) => {
    try {
      const blob = await api.downloadEvidence(versionId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = originalName;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      alert(`Error en descarga: ${err.message}`);
    }
  };

  // Abrir Modal de Calificación
  const handleOpenEval = (version) => {
    setEvalVersionId(version.id);
    setEvalScore(version.evaluacion ? version.evaluacion.puntaje_obtenido : '');
    setEvalResult(version.evaluacion ? version.evaluacion.resultado : 'APROBADO');
    setEvalObs(version.evaluacion ? version.evaluacion.observaciones || '' : '');
    setEvalRec(version.evaluacion ? version.evaluacion.recomendaciones || '' : '');
    setEvalError(null);
    setShowEvalModal(true);
  };

  const handleSaveEval = async (e) => {
    e.preventDefault();
    setEvalError(null);
    try {
      await api.evaluateVersion({
        version_id: evalVersionId,
        puntaje_obtenido: parseFloat(evalScore),
        resultado: evalResult,
        observaciones: evalObs,
        recomendaciones: evalRec
      });

      setShowEvalModal(false);
      await loadEvidence(selectedAct.id, selectedInscId);
      alert('Calificación y retroalimentación guardadas con éxito.');
    } catch (err) {
      setEvalError(err.message);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1>Gestión de Evidencias y Calificaciones</h1>
        <p style={{ color: 'var(--text-sec)' }}>
          Carga privada de entregables, control estricto de versiones y retroalimentación académica.
        </p>
      </div>

      {/* Selectores de Contexto */}
      <div className="card" style={{ marginBottom: '24px', padding: '18px 24px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
          {['ADMIN', 'COORDINADOR', 'TUTOR'].includes(role) && (
            <div>
              <label className="form-label">Seleccionar Postulante</label>
              <select
                className="form-select"
                value={selectedInscId || ''}
                onChange={(e) => setSelectedInscId(parseInt(e.target.value))}
              >
                {applicants.map((app) => (
                  <option key={app.id} value={app.id}>
                    {app.nombre_completo} ({app.programa_codigo}) - Riesgo {app.nivel_riesgo}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="form-label">Actividad o Proyecto</label>
            <select
              className="form-select"
              value={selectedAct?.id || ''}
              onChange={(e) => {
                const act = activities.find(a => a.id === parseInt(e.target.value));
                setSelectedAct(act);
              }}
            >
              {activities.map((act) => (
                <option key={act.id} value={act.id}>
                  {act.titulo} ({act.ponderacion}%)
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Panel Principal de Evidencia */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h3>{selectedAct?.titulo || 'Actividad seleccionada'}</h3>
            <small style={{ color: 'var(--text-sec)' }}>
              Ponderación: {selectedAct?.ponderacion}% • Formatos: <code>{selectedAct?.extensiones_permitidas}</code> • Límite: {selectedAct ? new Date(selectedAct.fecha_limite).toLocaleDateString() : ''}
            </small>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Badge type={evidenceData?.estado_entrega || 'PENDIENTE'} />
            
            {role === 'POSTULANTE' && (
              <button
                className="btn btn-primary"
                onClick={() => { setUploadError(null); setShowUploadModal(true); }}
              >
                <Upload size={16} />
                <span>{evidenceData?.numero_versiones > 0 ? 'Reenviar Corrección' : 'Cargar Evidencia'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Versiones de Entrega */}
        {(!evidenceData || evidenceData.versiones.length === 0) ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-sec)', background: 'var(--surface-muted)', borderRadius: '16px' }}>
            <FileText size={40} color="var(--text-sec)" style={{ margin: '0 auto 12px' }} />
            <p>No se han registrado versiones entregadas para esta actividad.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {evidenceData.versiones.map((v) => (
              <div
                key={v.id}
                style={{
                  border: '1px solid var(--border-light)',
                  borderRadius: '16px',
                  padding: '18px',
                  background: '#FFFFFF'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <strong>Versión {v.numero_version}</strong>
                      <span style={{ color: 'var(--text-sec)', fontSize: '0.85rem' }}>({(v.tamano_bytes / 1024).toFixed(1)} KB)</span>
                      {v.es_tardia && <Badge type="MEDIO" text="ENTREGA TARDÍA" />}
                    </div>
                    <small style={{ color: 'var(--text-sec)' }}>
                      Archivo: <code>{v.nombre_archivo_original}</code> • Entregado: {new Date(v.fecha_entrega).toLocaleString()}
                    </small>
                  </div>

                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                      className="btn btn-outline"
                      style={{ padding: '8px 12px', fontSize: '0.825rem' }}
                      onClick={() => handleDownloadFile(v.id, v.nombre_archivo_original)}
                    >
                      <Download size={14} />
                      <span>Descargar Privado</span>
                    </button>

                    {['ADMIN', 'COORDINADOR', 'TUTOR'].includes(role) && (
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '8px 12px', fontSize: '0.825rem' }}
                        onClick={() => handleOpenEval(v)}
                      >
                        <CheckCircle size={14} />
                        <span>{v.evaluacion ? 'Modificar Calificación' : 'Calificar'}</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Retroalimentación si existe */}
                {v.evaluacion && (
                  <div style={{
                    marginTop: '14px',
                    padding: '14px',
                    backgroundColor: 'var(--surface-muted)',
                    borderRadius: '12px',
                    borderLeft: `4px solid ${v.evaluacion.resultado === 'APROBADO' ? 'var(--status-success-text)' : 'var(--status-warning-text)'}`
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 600 }}>
                        Calificación: {v.evaluacion.puntaje_obtenido} / {selectedAct?.ponderacion} pts
                      </span>
                      <Badge type={v.evaluacion.resultado} />
                    </div>
                    {v.evaluacion.observaciones && (
                      <p style={{ fontSize: '0.875rem', marginTop: '6px' }}>
                        <strong>Observaciones:</strong> {v.evaluacion.observaciones}
                      </p>
                    )}
                    {v.evaluacion.recomendaciones && (
                      <p style={{ fontSize: '0.875rem', marginTop: '4px', color: 'var(--status-success-text)' }}>
                        <strong>Recomendaciones:</strong> {v.evaluacion.recomendaciones}
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal Subida de Evidencia (Postulante) */}
      <Modal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        title={`Cargar Evidencia: ${selectedAct?.titulo}`}
      >
        {uploadError && (
          <div style={{ background: 'var(--status-danger-bg)', color: 'var(--status-danger-text)', padding: '10px', borderRadius: '8px', marginBottom: '14px', fontSize: '0.875rem' }}>
            {uploadError}
          </div>
        )}
        <form onSubmit={handleUploadSubmit}>
          <div className="form-group">
            <label className="form-label">Seleccionar Archivo ({selectedAct?.extensiones_permitidas})</label>
            <input
              type="file"
              className="form-input"
              onChange={(e) => setUploadFile(e.target.files[0])}
              required
            />
            <small style={{ color: 'var(--text-sec)', marginTop: '4px', display: 'block' }}>
              El archivo se almacenará de manera cifrada en la partición privada del servidor institucional.
            </small>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn btn-outline" onClick={() => setShowUploadModal(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={uploading}>
              {uploading ? 'Cargando y calculando SHA-256...' : 'Confirmar Entrega'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Calificación (Tutor) */}
      <Modal
        isOpen={showEvalModal}
        onClose={() => setShowEvalModal(false)}
        title="Evaluar y Calificar Evidencia"
      >
        {evalError && (
          <div style={{ background: 'var(--status-danger-bg)', color: 'var(--status-danger-text)', padding: '10px', borderRadius: '8px', marginBottom: '14px', fontSize: '0.875rem' }}>
            {evalError}
          </div>
        )}
        <form onSubmit={handleSaveEval}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label className="form-label">Calificación (Ponderación máx: {selectedAct?.ponderacion})</label>
              <input
                type="number"
                step="0.01"
                min="0"
                max={selectedAct?.ponderacion}
                className="form-input"
                value={evalScore}
                onChange={(e) => setEvalScore(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Resultado</label>
              <select className="form-select" value={evalResult} onChange={(e) => setEvalResult(e.target.value)}>
                <option value="APROBADO">Aprobado</option>
                <option value="REQUIERE_CORRECCION">Requiere Corrección</option>
                <option value="RECHAZADO">Rechazado</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Observaciones Académicas</label>
            <textarea
              className="form-textarea"
              rows={2}
              placeholder="Retroalimentación técnica sobre la entrega..."
              value={evalObs}
              onChange={(e) => setEvalObs(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Recomendaciones para el Postulante</label>
            <textarea
              className="form-textarea"
              rows={2}
              placeholder="Consejos o pautas para futuras actividades..."
              value={evalRec}
              onChange={(e) => setEvalRec(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn btn-outline" onClick={() => setShowEvalModal(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary">
              Guardar Evaluación
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
