import React, { useState, useEffect } from 'react';
import { Award, Download, CheckCircle2, Undo2 } from 'lucide-react';
import { api } from '../services/api';
import { saveBlob } from '../utils/download';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

const ESTADO = {
  PENDIENTE: { type: 'PENDIENTE', text: 'Esperando verificación del tutor' },
  APROBADO: { type: 'APROBADO', text: 'Verificado' },
  DEVUELTO: { type: 'REQUIERE_CORRECCION', text: 'Devuelto por el tutor' },
};

function BarraMaestria({ porcentaje, aprobados, total }) {
  return (
    <div className="card" style={{ padding: '22px', marginBottom: '18px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px', flexWrap: 'wrap' }}>
        <h3>Avance de la maestría</h3>
        <strong style={{ fontSize: '1.6rem', color: 'var(--color-uide)' }}>{porcentaje}%</strong>
      </div>
      <div style={{ height: '12px', background: 'var(--surface-muted)', borderRadius: '6px', overflow: 'hidden', margin: '10px 0 6px' }}>
        <div style={{ width: `${porcentaje}%`, height: '100%', background: 'var(--color-uide)' }} />
      </div>
      <small>{aprobados} de {total} certificados de curso verificados por el tutor.</small>
    </div>
  );
}

/** Postulante: sus certificados por curso. Tutor y coordinación: certificados que esperan verificación. */
export default function CertificatesPage({ user }) {
  const role = user?.rol?.codigo;
  const esPostulante = role === 'POSTULANTE';
  const [inscripciones, setInscripciones] = useState([]);
  const [inscId, setInscId] = useState(null);
  const [datos, setDatos] = useState(null);
  const [pendientes, setPendientes] = useState([]);
  const [message, setMessage] = useState(null);
  const [devolver, setDevolver] = useState(null);
  const [observacion, setObservacion] = useState('');

  const cargarPostulante = async (id) => {
    try {
      setDatos(await api.getCertificates(id));
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  const cargarPendientes = async () => {
    try {
      setPendientes(await api.getPendingCertificates());
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  useEffect(() => {
    if (esPostulante) {
      api.getMyEnrollments().then((lista) => {
        const vigentes = lista.filter((i) => i.estado_proceso !== 'RETIRADO');
        setInscripciones(vigentes);
        if (vigentes.length) { setInscId(vigentes[0].id); cargarPostulante(vigentes[0].id); }
      }).catch((err) => setMessage({ type: 'error', text: err.message }));
    } else {
      cargarPendientes();
    }
  }, []);

  const descargar = async (c) => {
    try {
      saveBlob(await api.downloadCourseCertificate(c.asignacion_id), `certificado_${c.curso_codigo}.pdf`);
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  const revisar = async (c, aprobar, obs = null) => {
    setMessage(null);
    try {
      await api.reviewCertificate(c.asignacion_id, { aprobar, observacion: obs });
      setMessage({ type: 'success', text: aprobar ? `Certificado de ${c.postulante_nombre} verificado.` : 'Certificado devuelto con su observación.' });
      setDevolver(null);
      cargarPendientes();
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}><Award size={26} /> Certificados</h1>
        <p style={{ color: 'var(--text-sec)' }}>
          {esPostulante
            ? 'Al aprobar cada curso preparatorio (70/100) se emite su certificado. Cuando su tutor lo verifica, cuenta para el avance de la maestría.'
            : 'Certificados de los cursos a su cargo que esperan su verificación. Al verificarlos cuentan para el avance de la maestría del postulante.'}
        </p>
      </div>

      {message && (
        <div className={message.type === 'error' ? 'notice-danger' : 'notice-success'} style={{ marginBottom: '16px' }}>{message.text}</div>
      )}

      {esPostulante && (
        <>
          {inscripciones.length > 1 && (
            <div className="form-group" style={{ maxWidth: '420px' }}>
              <label className="form-label">Maestría</label>
              <select className="form-select" value={inscId || ''} onChange={(e) => { setInscId(parseInt(e.target.value)); cargarPostulante(parseInt(e.target.value)); }}>
                {inscripciones.map((i) => <option key={i.id} value={i.id}>{i.programa_nombre} · {i.convocatoria_nombre}</option>)}
              </select>
            </div>
          )}
          {inscripciones.length === 0 && <div className="card" style={{ padding: '24px' }}>Todavía no tiene una inscripción vigente.</div>}
          {datos && (
            <>
              <BarraMaestria porcentaje={datos.porcentaje_maestria} aprobados={datos.certificados_aprobados} total={datos.total_cursos} />
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '14px' }}>
                {datos.cursos.map((c) => (
                  <div key={c.asignacion_id} className="card" style={{ padding: '18px', borderTop: `4px solid ${c.certificado_estado === 'APROBADO' ? 'var(--color-gold)' : 'var(--border-light)'}` }}>
                    <small style={{ color: 'var(--text-sec)' }}>{c.curso_codigo}</small>
                    <h3 style={{ margin: '2px 0 8px' }}>{c.curso_nombre}</h3>
                    {c.certificado_estado ? (
                      <>
                        <Badge type={ESTADO[c.certificado_estado].type} text={ESTADO[c.certificado_estado].text} />
                        <p style={{ fontSize: '0.875rem', margin: '8px 0' }}>Nota del curso: <strong>{c.nota_final}/100</strong></p>
                        {c.observacion && c.certificado_estado === 'DEVUELTO' && (
                          <p style={{ fontSize: '0.85rem', color: 'var(--status-warning-text)' }}>{c.observacion}</p>
                        )}
                        <button className="btn btn-outline" onClick={() => descargar(c)}><Download size={15} /> Descargar PDF</button>
                      </>
                    ) : (
                      <>
                        <Badge type="EN_CURSO" text="Curso en progreso" />
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-sec)', marginTop: '8px' }}>
                          El certificado aparecerá aquí cuando apruebe el curso.
                        </p>
                      </>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}

      {!esPostulante && (
        <div className="card" style={{ padding: '20px' }}>
          {pendientes.length === 0 ? (
            <p style={{ color: 'var(--text-sec)' }}>No hay certificados esperando su verificación.</p>
          ) : (
            <div className="table-responsive" style={{ border: 'none' }}>
              <table className="table">
                <thead>
                  <tr><th>Postulante</th><th>Curso</th><th>Nota</th><th>Emitido</th><th style={{ textAlign: 'center' }}>Acciones</th></tr>
                </thead>
                <tbody>
                  {pendientes.map((c) => (
                    <tr key={c.asignacion_id}>
                      <td><strong>{c.postulante_nombre}</strong><div><small>{c.programa}</small></div></td>
                      <td>{c.curso_nombre}</td>
                      <td>{c.nota_final}/100</td>
                      <td>{c.emitido_en ? new Date(c.emitido_en).toLocaleDateString() : '-'}</td>
                      <td style={{ textAlign: 'center' }}>
                        <div style={{ display: 'inline-flex', gap: '6px' }}>
                          <button className="btn btn-outline" style={{ padding: '6px 8px' }} title="Ver PDF" onClick={() => descargar(c)}><Download size={15} /></button>
                          <button className="btn btn-primary" style={{ padding: '6px 10px' }} onClick={() => revisar(c, true)}><CheckCircle2 size={15} /> Verificar</button>
                          <button className="btn btn-outline" style={{ padding: '6px 8px' }} title="Devolver" onClick={() => { setDevolver(c); setObservacion(''); }}><Undo2 size={15} /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <Modal isOpen={!!devolver} onClose={() => setDevolver(null)} title={`Devolver certificado - ${devolver?.postulante_nombre || ''}`}>
        <form onSubmit={(e) => { e.preventDefault(); revisar(devolver, false, observacion); }}>
          <div className="form-group">
            <label className="form-label">¿Qué hay que revisar?</label>
            <textarea className="form-textarea" rows={3} value={observacion} onChange={(e) => setObservacion(e.target.value)} minLength={5} required />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button type="button" className="btn btn-outline" onClick={() => setDevolver(null)}>Cancelar</button>
            <button type="submit" className="btn btn-primary">Devolver</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
