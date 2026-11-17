import React, { useState, useEffect } from 'react';
import { ShieldAlert, RefreshCw, CheckCircle, Forward } from 'lucide-react';
import { api } from '../services/api';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

const TIPO_TEXTO = {
  INACTIVIDAD: 'Inactividad',
  CONTACTO_SIN_RESPUESTA: 'Sin respuesta a contactos',
  SIN_EVIDENCIA: 'Actividad vencida sin evidencia',
  BAJO_AVANCE: 'Bajo avance',
  VENCIMIENTO_PROXIMO: 'Vencimiento',
  COMPROMISO_VENCIDO: 'Compromiso vencido',
};

export default function AlertsPage({ user }) {
  const role = user?.rol?.codigo;
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showResolved, setShowResolved] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [message, setMessage] = useState(null);

  const [selected, setSelected] = useState(null);
  const [accion, setAccion] = useState('');
  const [resolveError, setResolveError] = useState(null);

  // Derivar a un coordinador
  const [derivar, setDerivar] = useState(null); // { alerta, destinatarios, destinatario_id, nota }
  const [derivarError, setDerivarError] = useState(null);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      setAlerts(await api.getRiskAlerts(showResolved));
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, [showResolved]);

  const handleEvaluate = async () => {
    try {
      setEvaluating(true);
      const res = await api.evaluateRisks();
      const r = res.resumen;
      setMessage({ type: 'success', text: `Evaluación completa: ${r.evaluados} postulantes (${r.alto} en riesgo alto, ${r.medio} medio, ${r.bajo} bajo).` });
      loadAlerts();
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setEvaluating(false);
    }
  };

  const handleResolve = async (e) => {
    e.preventDefault();
    try {
      await api.resolveRiskAlert(selected.id, accion);
      setSelected(null);
      loadAlerts();
    } catch (err) {
      setResolveError(err.message);
    }
  };

  const handleOpenDerivar = async (a) => {
    setDerivarError(null);
    try {
      const destinatarios = await api.getAlertRecipients(a.id);
      setDerivar({ alerta: a, destinatarios, destinatario_id: destinatarios[0]?.id || '', nota: '' });
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  const handleDerivar = async (e) => {
    e.preventDefault();
    try {
      await api.deriveAlert(derivar.alerta.id, Number(derivar.destinatario_id), derivar.nota);
      setMessage({ type: 'success', text: 'Alerta derivada. Se avisó por correo al coordinador.' });
      setDerivar(null);
      loadAlerts();
    } catch (err) {
      setDerivarError(err.message);
    }
  };

  const abiertas = alerts.filter((a) => !a.resuelta);
  const altas = abiertas.filter((a) => a.nivel_riesgo === 'ALTO').length;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1>Alertas de Riesgo</h1>
          <p style={{ color: 'var(--text-sec)' }}>
            Se abren y se cierran solas según la situación de cada postulante. Resuelva a mano solo las que atendió.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.875rem', color: 'var(--text-sec)' }}>
            <input type="checkbox" checked={showResolved} onChange={(e) => setShowResolved(e.target.checked)} />
            Ver resueltas
          </label>
          {['ADMIN', 'COORDINADOR'].includes(role) && (
            <button className="btn btn-primary" onClick={handleEvaluate} disabled={evaluating}>
              <RefreshCw size={16} className={evaluating ? 'spin' : ''} />
              <span>Evaluar riesgos ahora</span>
            </button>
          )}
        </div>
      </div>

      {message && (
        <div
          className={message.type === 'error' ? 'notice-danger' : 'notice-success'}
          style={{ marginBottom: '18px' }}
          onClick={() => setMessage(null)}
        >
          <span>{message.text}</span>
        </div>
      )}

      <div className="grid-cols-4" style={{ marginBottom: '24px' }}>
        <div className="card">
          <small style={{ color: 'var(--text-sec)', fontWeight: 600 }}>ALERTAS ABIERTAS</small>
          <h2 style={{ marginTop: '4px' }}>{abiertas.length}</h2>
        </div>
        <div className="card">
          <small style={{ color: 'var(--text-sec)', fontWeight: 600 }}>RIESGO ALTO</small>
          <h2 style={{ marginTop: '4px', color: 'var(--status-danger-text)' }}>{altas}</h2>
        </div>
        <div className="card">
          <small style={{ color: 'var(--text-sec)', fontWeight: 600 }}>RIESGO MEDIO</small>
          <h2 style={{ marginTop: '4px' }}>{abiertas.length - altas}</h2>
        </div>
        <div className="card">
          <small style={{ color: 'var(--text-sec)', fontWeight: 600 }}>POSTULANTES AFECTADOS</small>
          <h2 style={{ marginTop: '4px' }}>{new Set(abiertas.map((a) => a.inscripcion_id)).size}</h2>
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center' }}>Cargando alertas...</div>
        ) : alerts.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-sec)' }}>
            <ShieldAlert size={28} style={{ marginBottom: '8px' }} />
            <div>No hay alertas abiertas para sus postulantes.</div>
          </div>
        ) : (
          <div className="table-responsive" style={{ border: 'none' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Detectada</th>
                  <th>Postulante</th>
                  <th>Tipo</th>
                  <th>Nivel</th>
                  <th>Detalle</th>
                  <th style={{ textAlign: 'center' }}>Acción</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((a) => (
                  <tr key={a.id} style={a.resuelta ? { opacity: 0.65 } : undefined}>
                    <td style={{ whiteSpace: 'nowrap' }}>{new Date(a.fecha_deteccion).toLocaleString()}</td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{a.postulante_nombre}</div>
                      <small style={{ color: 'var(--text-sec)' }}>{a.programa_codigo}</small>
                    </td>
                    <td>{TIPO_TEXTO[a.tipo_alerta] || a.tipo_alerta}</td>
                    <td><Badge type={a.nivel_riesgo} /></td>
                    <td style={{ maxWidth: '360px' }}>
                      <small>{a.motivo_detallado}</small>
                      {a.derivada_a_nombre && (
                        <div><small style={{ color: 'var(--color-navy)' }}>
                          Derivada a {a.derivada_a_nombre}{a.nota_derivacion ? `: ${a.nota_derivacion}` : ''}
                        </small></div>
                      )}
                      {a.resuelta && (
                        <div><small style={{ color: 'var(--text-sec)' }}>
                          Resuelta {a.resuelta_por_nombre ? `por ${a.resuelta_por_nombre}` : ''}: {a.accion_tomada}
                        </small></div>
                      )}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      {a.resuelta ? (
                        <Badge type="APROBADO" text="RESUELTA" />
                      ) : (
                        <div style={{ display: 'inline-flex', gap: '6px' }}>
                          <button
                            className="btn btn-outline"
                            style={{ padding: '6px 10px', fontSize: '0.8rem' }}
                            onClick={() => { setSelected(a); setAccion(''); setResolveError(null); }}
                          >
                            <CheckCircle size={15} />
                            <span>Resolver</span>
                          </button>
                          {role !== 'ADMIN' && (
                            <button
                              className="btn btn-outline"
                              style={{ padding: '6px 10px', fontSize: '0.8rem' }}
                              title="Pedir ayuda a coordinación con este caso"
                              onClick={() => handleOpenDerivar(a)}
                            >
                              <Forward size={15} />
                              <span>Derivar</span>
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Modal isOpen={!!selected} onClose={() => setSelected(null)} title={`Resolver alerta - ${selected?.postulante_nombre || ''}`}>
        <form onSubmit={handleResolve}>
          {resolveError && <div className="notice-danger" style={{ marginBottom: '14px' }}>{resolveError}</div>}
          <p style={{ fontSize: '0.875rem', color: 'var(--text-sec)', marginBottom: '14px' }}>{selected?.motivo_detallado}</p>
          <div className="form-group">
            <label className="form-label">Acción tomada</label>
            <textarea
              className="form-textarea"
              rows={3}
              value={accion}
              onChange={(e) => setAccion(e.target.value)}
              placeholder="Ej.: Reunión con el postulante; se comprometió a entregar el taller el viernes."
              required
              minLength={5}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn btn-outline" onClick={() => setSelected(null)}>Cancelar</button>
            <button type="submit" className="btn btn-primary">Marcar como resuelta</button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={!!derivar} onClose={() => setDerivar(null)} title={`Derivar alerta - ${derivar?.alerta.postulante_nombre || ''}`}>
        {derivar && (
          <form onSubmit={handleDerivar}>
            {derivarError && <div className="notice-danger" style={{ marginBottom: '14px' }}>{derivarError}</div>}
            {derivar.destinatarios.length === 0 ? (
              <p style={{ color: 'var(--text-sec)' }}>Este programa no tiene otro coordinador a quien derivar.</p>
            ) : (
              <>
                <div className="form-group">
                  <label className="form-label">Coordinador</label>
                  <select className="form-select" value={derivar.destinatario_id} onChange={(e) => setDerivar({ ...derivar, destinatario_id: e.target.value })}>
                    {derivar.destinatarios.map((d) => <option key={d.id} value={d.id}>{d.nombre_completo}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Qué pasó y qué necesita</label>
                  <textarea className="form-textarea" rows={3} minLength={5} required value={derivar.nota}
                    onChange={(e) => setDerivar({ ...derivar, nota: e.target.value })} />
                </div>
              </>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
              <button type="button" className="btn btn-outline" onClick={() => setDerivar(null)}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={derivar.destinatarios.length === 0}>Derivar</button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
