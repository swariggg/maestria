import React, { useState, useEffect } from 'react';
import { ClipboardList, CalendarDays, BookOpen } from 'lucide-react';
import { api } from '../services/api';
import Badge from '../components/Badge';

export default function EnrollmentPage() {
  const [convocatorias, setConvocatorias] = useState([]);
  const [misInscripciones, setMisInscripciones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [enrollingId, setEnrollingId] = useState(null);
  const [message, setMessage] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [abiertas, mias] = await Promise.all([api.getOpenCalls(), api.getMyEnrollments()]);
      setConvocatorias(abiertas);
      setMisInscripciones(mias);
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleEnroll = async (conv) => {
    try {
      setEnrollingId(conv.id);
      setMessage(null);
      const res = await api.enroll({ convocatoria_id: conv.id });
      setMessage({
        type: 'success',
        text: `Inscripción registrada en ${res.convocatoria_nombre}. Cursos asignados: ${res.cursos.join(', ')}.`
      });
      await loadData();
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setEnrollingId(null);
    }
  };

  const tieneInscripcionVigente = misInscripciones.some((i) => i.estado_proceso !== 'RETIRADO');

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '60px' }}>Cargando convocatorias...</div>;
  }

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1>Inscripción a Programas de Maestría</h1>
        <p style={{ color: 'var(--text-sec)' }}>
          Seleccione una convocatoria abierta. Los cursos preparatorios se asignan automáticamente al inscribirse.
        </p>
      </div>

      {message && (
        <div style={{
          background: message.type === 'success' ? 'var(--status-success-bg)' : 'var(--status-danger-bg)',
          color: message.type === 'success' ? 'var(--status-success-text)' : 'var(--status-danger-text)',
          padding: '12px 16px',
          borderRadius: '12px',
          marginBottom: '20px'
        }}>
          {message.text}
        </div>
      )}

      {misInscripciones.length > 0 && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <h3 style={{ marginBottom: '12px' }}>Mis Inscripciones</h3>
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Programa</th>
                  <th>Convocatoria</th>
                  <th>Fecha de Inscripción</th>
                  <th>Cursos Asignados</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {misInscripciones.map((i) => (
                  <tr key={i.id}>
                    <td style={{ fontWeight: 600 }}>{i.programa_nombre}</td>
                    <td>{i.convocatoria_nombre}</td>
                    <td>{new Date(i.fecha_inscripcion).toLocaleDateString()}</td>
                    <td>{i.cursos.join(', ') || '—'}</td>
                    <td><Badge type={i.estado_proceso} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <h3 style={{ marginBottom: '12px' }}>Convocatorias Abiertas</h3>
      {convocatorias.length === 0 ? (
        <div className="card">
          <p style={{ color: 'var(--text-sec)' }}>No hay convocatorias abiertas en este momento.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
          {convocatorias.map((conv) => {
            const sinCursos = conv.cursos.length === 0;
            return (
              <div className="card" key={conv.id}>
                <Badge type="ABIERTA" text={conv.programa_codigo} />
                <h3 style={{ marginTop: '10px' }}>{conv.programa_nombre}</h3>
                <p style={{ color: 'var(--text-sec)', marginBottom: '12px' }}>{conv.nombre}</p>

                <small style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-sec)' }}>
                  <CalendarDays size={14} /> Inscripciones hasta {conv.fecha_cierre}
                </small>
                <small style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-sec)', marginTop: '4px' }}>
                  <CalendarDays size={14} /> Preparatorio: {conv.fecha_inicio_preparatorio} al {conv.fecha_fin_preparatorio}
                </small>
                <small style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', color: 'var(--text-sec)', marginTop: '4px' }}>
                  <BookOpen size={14} style={{ flexShrink: 0, marginTop: '2px' }} />
                  {sinCursos ? 'Aún sin cursos preparatorios configurados' : conv.cursos.join(', ')}
                </small>

                <div style={{ marginTop: '16px' }}>
                  {conv.inscrito ? (
                    <Badge type="APROBADO" text="YA INSCRITO" />
                  ) : (
                    <button
                      className="btn btn-primary"
                      style={{ width: '100%' }}
                      onClick={() => handleEnroll(conv)}
                      disabled={sinCursos || tieneInscripcionVigente || enrollingId !== null}
                      title={tieneInscripcionVigente ? 'Ya tiene una inscripción vigente' : undefined}
                    >
                      <ClipboardList size={16} />
                      {enrollingId === conv.id ? 'Inscribiendo...' : 'Inscribirme'}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
