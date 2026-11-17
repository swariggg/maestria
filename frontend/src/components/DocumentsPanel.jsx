import React, { useState, useEffect } from 'react';
import { Upload, Download, CheckCircle, FileText, RotateCcw } from 'lucide-react';
import { api } from '../services/api';
import { saveBlob } from '../utils/download';
import Badge from './Badge';

const ESTADO_TEXTO = {
  SIN_CARGAR: 'Sin cargar',
  PENDIENTE: 'En revisión',
  APROBADO: 'Aprobado',
  REQUIERE_CORRECCION: 'Requiere corrección',
  RECHAZADO: 'Rechazado',
};

/**
 * Requisitos documentales de una inscripción.
 * modo "postulante": sube y reemplaza documentos.
 * modo "revision": coordinación revisa y puede reabrir un documento; el tutor solo descarga (puedeRevisar = false).
 */
export default function DocumentsPanel({ inscripcionId, modo = 'postulante', onChange, puedeRevisar: rolRevisa = true }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [uploadingId, setUploadingId] = useState(null);
  const [review, setReview] = useState(null); // { documento, requisito, estado, observaciones }
  const [reopen, setReopen] = useState(null); // { documento, requisito, motivo }

  const load = async () => {
    try {
      setData(await api.getEnrollmentDocuments(inscripcionId));
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    if (inscripcionId) load();
  }, [inscripcionId]);

  const handleUpload = async (req, file) => {
    if (!file) return;
    setUploadingId(req.id);
    setMessage(null);
    try {
      const fd = new FormData();
      fd.append('inscripcion_id', inscripcionId);
      fd.append('requisito_id', req.id);
      fd.append('file', file);
      const res = await api.uploadDocument(fd);
      setMessage({ type: 'success', text: res.mensaje });
      await load();
      onChange?.();
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setUploadingId(null);
    }
  };

  const handleDownload = async (doc) => {
    try {
      saveBlob(await api.downloadDocument(doc.id), doc.nombre_original);
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  const handleReview = async (e) => {
    e.preventDefault();
    try {
      const res = await api.reviewDocument(review.documento.id, {
        estado_revision: review.estado,
        observaciones: review.observaciones || null,
      });
      setReview(null);
      setMessage({
        type: 'success',
        text: res.documentacion_completa
          ? `Documentación completa: la inscripción pasó a ${res.estado_proceso}.`
          : 'Revisión registrada y notificada al postulante.',
      });
      await load();
      onChange?.();
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  const handleReopen = async (e) => {
    e.preventDefault();
    try {
      const res = await api.reopenDocument(reopen.documento.id, reopen.motivo);
      setReopen(null);
      setMessage({ type: 'success', text: res.mensaje || 'Documento reabierto. El postulante puede volver a subirlo.' });
      await load();
      onChange?.();
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  if (error) return <div className="notice-danger">{error}</div>;
  if (!data) return <div style={{ padding: '20px', textAlign: 'center' }}>Cargando documentos...</div>;

  const obligatorios = data.requisitos.filter((r) => r.es_obligatorio);
  const aprobados = obligatorios.filter((r) => r.estado === 'APROBADO').length;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '14px' }}>
        <small style={{ color: 'var(--text-sec)' }}>
          {data.convocatoria_nombre} · Obligatorios aprobados: <strong>{aprobados} de {obligatorios.length}</strong>
        </small>
        <Badge
          type={data.documentacion_completa ? 'APROBADO' : 'DOCUMENTACION_PENDIENTE'}
          text={data.documentacion_completa ? 'Documentación completa' : 'Documentación pendiente'}
        />
      </div>

      {message && (
        <div className={message.type === 'error' ? 'notice-danger' : 'notice-success'} style={{ marginBottom: '14px' }}>
          {message.text}
        </div>
      )}

      {data.requisitos.length === 0 ? (
        <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-sec)' }}>
          Esta convocatoria no pide documentos.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {data.requisitos.map((req) => {
            const doc = req.documento;
            const subida = req.estado_subida || {};
            const puedeSubir = modo === 'postulante' && subida.puede_subir;
            const puedeRevisar = modo === 'revision' && rolRevisa && doc && doc.estado_revision === 'PENDIENTE' && data.puede_subir;
            const puedeReabrir = modo === 'revision' && rolRevisa && doc && ['APROBADO', 'RECHAZADO'].includes(doc.estado_revision) && data.puede_subir;
            return (
              <div key={req.id} style={{ padding: '14px 16px', borderRadius: '14px', border: '1px solid var(--border-light)', background: 'var(--surface-muted)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', flexWrap: 'wrap' }}>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <FileText size={16} color="var(--color-navy)" />
                      <strong style={{ fontSize: '0.925rem' }}>{req.nombre}</strong>
                      {!req.es_obligatorio && <Badge type="BAJO" text="Opcional" />}
                    </div>
                    {req.descripcion && <small style={{ display: 'block', marginTop: '4px' }}>{req.descripcion}</small>}
                    <small style={{ display: 'block', color: 'var(--text-sec)', marginTop: '4px' }}>
                      Formatos: <code>{req.formato_permitido}</code> · Máximo {req.tamano_max_mb} MB
                    </small>
                    {doc && (
                      <small style={{ display: 'block', marginTop: '6px' }}>
                        Archivo: <strong>{doc.nombre_original}</strong> · {new Date(doc.fecha_carga).toLocaleString()}
                        {doc.revisado_por && ` · Revisado por ${doc.revisado_por}`}
                      </small>
                    )}
                    {subida.intentos_usados > 0 && (
                      <small style={{ display: 'block', color: 'var(--text-sec)', marginTop: '4px' }}>
                        Intentos: {subida.intentos_usados} de {data.max_intentos} · Le quedan {subida.intentos_restantes}
                      </small>
                    )}
                    {modo === 'postulante' && subida.motivo_bloqueo && req.estado !== 'APROBADO' && (
                      <small style={{ display: 'block', marginTop: '4px', color: 'var(--status-danger-text)' }}>
                        {subida.motivo_bloqueo}
                      </small>
                    )}
                    {doc?.observaciones && (
                      <small style={{ display: 'block', marginTop: '4px', color: 'var(--status-warning-text)' }}>
                        Observaciones: {doc.observaciones}
                      </small>
                    )}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <Badge type={req.estado === 'SIN_CARGAR' ? 'PENDIENTE' : req.estado} text={ESTADO_TEXTO[req.estado] || req.estado} />
                    {doc && (
                      <button className="btn btn-outline" style={{ padding: '6px 10px', fontSize: '0.8rem' }} onClick={() => handleDownload(doc)}>
                        <Download size={14} />
                      </button>
                    )}
                    {puedeSubir && (
                      <label className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem', cursor: 'pointer' }}>
                        <Upload size={14} />
                        <span>{uploadingId === req.id ? 'Subiendo...' : doc ? 'Reemplazar' : 'Subir'}</span>
                        <input
                          type="file"
                          hidden
                          accept={req.formato_permitido.split(',').map((f) => `.${f}`).join(',')}
                          disabled={uploadingId === req.id}
                          onChange={(e) => { handleUpload(req, e.target.files[0]); e.target.value = ''; }}
                        />
                      </label>
                    )}
                    {puedeReabrir && (
                      <button
                        className="btn btn-outline"
                        style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                        title="Permite al postulante volver a subir este documento"
                        onClick={() => setReopen({ documento: doc, requisito: req, motivo: '' })}
                      >
                        <RotateCcw size={14} />
                        <span>Reabrir</span>
                      </button>
                    )}
                    {puedeRevisar && (
                      <button
                        className="btn btn-primary"
                        style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                        onClick={() => setReview({ documento: doc, requisito: req, estado: 'APROBADO', observaciones: '' })}
                      >
                        <CheckCircle size={14} />
                        <span>Revisar</span>
                      </button>
                    )}
                  </div>
                </div>

                {reopen?.requisito.id === req.id && (
                  <form onSubmit={handleReopen} style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-light)' }}>
                    <input
                      className="form-input"
                      placeholder="Motivo de la reapertura (se envía al postulante)"
                      value={reopen.motivo}
                      onChange={(e) => setReopen({ ...reopen, motivo: e.target.value })}
                      minLength={5}
                      required
                    />
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '10px' }}>
                      <button type="button" className="btn btn-outline" onClick={() => setReopen(null)}>Cancelar</button>
                      <button type="submit" className="btn btn-primary">Reabrir documento</button>
                    </div>
                  </form>
                )}

                {review?.requisito.id === req.id && (
                  <form onSubmit={handleReview} style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-light)' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(160px, 1fr) 2fr', gap: '10px' }}>
                      <select className="form-select" value={review.estado} onChange={(e) => setReview({ ...review, estado: e.target.value })}>
                        <option value="APROBADO">Aprobar</option>
                        <option value="REQUIERE_CORRECCION">Requiere corrección</option>
                        <option value="RECHAZADO">Rechazar (definitivo)</option>
                      </select>
                      <input
                        className="form-input"
                        placeholder={review.estado === 'APROBADO' ? 'Observaciones (opcional)' : 'Qué debe corregir el postulante'}
                        value={review.observaciones}
                        onChange={(e) => setReview({ ...review, observaciones: e.target.value })}
                        required={review.estado !== 'APROBADO'}
                      />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '10px' }}>
                      <button type="button" className="btn btn-outline" onClick={() => setReview(null)}>Cancelar</button>
                      <button type="submit" className="btn btn-primary">Guardar revisión</button>
                    </div>
                  </form>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
