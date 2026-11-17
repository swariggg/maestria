import React, { useState, useEffect } from 'react';
import { 
  Users, 
  BookOpen, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  MessageSquareWarning, 
  RefreshCw,
  Calendar,
  FileCheck2,
  Video
} from 'lucide-react';
import { api } from '../services/api';
import Badge from '../components/Badge';

export default function DashboardPage({ user, onNavigate }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [evalMessage, setEvalMessage] = useState(null);
  const [misAlertas, setMisAlertas] = useState([]);

  const loadStats = async () => {
    try {
      setLoading(true);
      const data = await api.getStats();
      setStats(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
    if (user?.rol?.codigo === 'POSTULANTE') {
      api.getMyAlerts().then(setMisAlertas).catch(() => setMisAlertas([]));
    }
  }, []);

  const handleEvaluateRisks = async () => {
    try {
      setEvaluating(true);
      setEvalMessage(null);
      const res = await api.triggerRiskEvaluation();
      setEvalMessage(`Evaluación completa: ${res.resumen.alto} en Alto Riesgo, ${res.resumen.medio} en Medio Riesgo.`);
      await loadStats();
    } catch (err) {
      setEvalMessage(`Error: ${err.message}`);
    } finally {
      setEvaluating(false);
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '60px' }}>Cargando indicadores académicos...</div>;
  }

  const role = user?.rol?.codigo;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1>Panel de Control Académico</h1>
          <p style={{ color: 'var(--text-sec)' }}>
            Bienvenido, {user?.nombre_completo}. Resumen del estado actual del proceso preparatorio.
          </p>
        </div>

        {['ADMIN', 'COORDINADOR'].includes(role) && (
          <button
            onClick={handleEvaluateRisks}
            className="btn btn-secondary"
            disabled={evaluating}
          >
            <RefreshCw size={16} className={evaluating ? 'spin' : ''} />
            <span>{evaluating ? 'Evaluando...' : 'Recalcular Riesgos Ahora'}</span>
          </button>
        )}
      </div>

      {evalMessage && (
        <div style={{
          backgroundColor: 'var(--color-sec)',
          color: 'var(--color-sec-text)',
          padding: '12px 18px',
          borderRadius: '12px',
          marginBottom: '20px',
          fontSize: '0.9rem',
          fontWeight: 500
        }}>
          {evalMessage}
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid-cols-4" style={{ marginBottom: '28px' }}>
        <div className="card card-hero">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <small style={{ color: 'var(--text-sec)', fontWeight: 600 }}>TOTAL POSTULANTES</small>
              <h2 style={{ fontSize: '2rem', marginTop: '4px' }}>{stats?.total_postulantes || 0}</h2>
            </div>
            <div className="kpi-icon duo">
              <Users size={22} color="#FFFFFF" />
            </div>
          </div>
          <small style={{ color: 'var(--text-sec)', marginTop: '8px', display: 'block' }}>
            Registrados en el sistema
          </small>
        </div>

        <div className="card card-alert">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <small style={{ color: 'var(--text-sec)', fontWeight: 600 }}>RIESGO ALTO</small>
              <h2 style={{ fontSize: '2rem', marginTop: '4px', color: 'var(--status-danger-text)' }}>
                {stats?.postulantes_riesgo_alto || 0}
              </h2>
            </div>
            <div className="kpi-icon duo">
              <AlertTriangle size={22} color="var(--status-danger-text)" />
            </div>
          </div>
          <small style={{ color: 'var(--text-sec)', marginTop: '8px', display: 'block' }}>
            Inactividad (7d) o sin respuesta (2)
          </small>
        </div>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <small style={{ color: 'var(--text-sec)', fontWeight: 600 }}>RIESGO MEDIO</small>
              <h2 style={{ fontSize: '2rem', marginTop: '4px', color: 'var(--status-warning-text)' }}>
                {stats?.postulantes_riesgo_medio || 0}
              </h2>
            </div>
            <div className="kpi-icon duo">
              <Clock size={22} color="var(--status-warning-text)" />
            </div>
          </div>
          <small style={{ color: 'var(--text-sec)', marginTop: '8px', display: 'block' }}>
            Entregas próximas o pendientes
          </small>
        </div>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <small style={{ color: 'var(--text-sec)', fontWeight: 600 }}>
                {role === 'POSTULANTE' ? 'AVANCE ACADÉMICO' : 'SEGUIMIENTOS TOTALES'}
              </small>
              <h2 style={{ fontSize: '2rem', marginTop: '4px', color: 'var(--status-success-text)' }}>
                {role === 'POSTULANTE' ? `${stats?.porcentaje_cumplimiento_promedio || 0}%` : (stats?.seguimientos_totales || 0)}
              </h2>
            </div>
            <div className="kpi-icon duo">
              {role === 'POSTULANTE' ? <FileCheck2 size={22} color="var(--status-success-text)" /> : <MessageSquareWarning size={22} color="var(--status-success-text)" />}
            </div>
          </div>
          <small style={{ color: 'var(--text-sec)', marginTop: '8px', display: 'block' }}>
            {role === 'POSTULANTE' ? 'Actividades aprobadas' : `${stats?.seguimientos_sin_respuesta || 0} llamadas/mensajes sin respuesta`}
          </small>
        </div>
      </div>

      {role !== 'POSTULANTE' && (
        <div className="grid-cols-4" style={{ marginBottom: '28px' }}>
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <small style={{ color: 'var(--text-sec)', fontWeight: 600 }}>POSTULANTES APROBADOS</small>
                <h2 style={{ fontSize: '2rem', marginTop: '4px', color: 'var(--status-success-text)' }}>
                  {stats?.postulantes_aprobados || 0}
                </h2>
              </div>
              <div className="kpi-icon duo">
                <CheckCircle2 size={22} color="var(--status-success-text)" />
              </div>
            </div>
            <small style={{ color: 'var(--text-sec)', marginTop: '8px', display: 'block' }}>
              Aprobaron todos sus cursos preparatorios
            </small>
          </div>

          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <small style={{ color: 'var(--text-sec)', fontWeight: 600 }}>CUMPLIMIENTO PROMEDIO</small>
                <h2 style={{ fontSize: '2rem', marginTop: '4px' }}>
                  {stats?.porcentaje_cumplimiento_promedio || 0}%
                </h2>
              </div>
              <div className="kpi-icon duo">
                <FileCheck2 size={22} />
              </div>
            </div>
            <small style={{ color: 'var(--text-sec)', marginTop: '8px', display: 'block' }}>
              Actividades aprobadas sobre el total de sus cursos
            </small>
          </div>

          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <small style={{ color: 'var(--text-sec)', fontWeight: 600 }}>CURSOS ACTIVOS</small>
                <h2 style={{ fontSize: '2rem', marginTop: '4px' }}>
                  {stats?.cursos_activos || 0}
                </h2>
              </div>
              <div className="kpi-icon duo">
                <BookOpen size={22} />
              </div>
            </div>
            <small style={{ color: 'var(--text-sec)', marginTop: '8px', display: 'block' }}>
              Cursos preparatorios en marcha
            </small>
          </div>
        </div>
      )}

      {/* Casos Críticos o Próximos Vencimientos */}
      {role === 'POSTULANTE' ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px', alignItems: 'start' }}>
          <div style={{ gridColumn: 'span 2', minWidth: 0 }}>
            {stats?.inscripciones?.length > 1 && (
              <div className="card" style={{ marginBottom: '24px' }}>
                <h3 style={{ marginBottom: '12px' }}>Mis programas</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
                  {stats.inscripciones.map((i) => (
                    <div key={i.inscripcion_id} style={{ padding: '12px 14px', borderRadius: '14px', background: 'var(--surface-muted)', border: '1px solid var(--border-light)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', alignItems: 'center' }}>
                        <strong>{i.programa}</strong>
                        <Badge type={i.estado} />
                      </div>
                      <small style={{ color: 'var(--text-sec)' }}>{i.convocatoria} · Avance {i.porcentaje}%</small>
                    </div>
                  ))}
                </div>
              </div>
            )}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3>Mis Actividades y Fechas Límite</h3>
              <button className="btn btn-outline" onClick={() => onNavigate('evidences')}>
                Ir a Entregar Evidencias
              </button>
            </div>
            {stats?.proximos_vencimientos?.length > 0 ? (
              <div className="table-responsive">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Actividad</th>
                      <th>Tipo</th>
                      <th>Ponderación</th>
                      <th>Fecha Límite</th>
                      <th>Días Restantes</th>
                      <th>Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.proximos_vencimientos.map((act) => (
                      <tr key={`${act.inscripcion_id}-${act.actividad_id}`}>
                        <td>
                          <div style={{ fontWeight: 600 }}>{act.titulo}</div>
                          {act.curso && <small style={{ color: 'var(--text-sec)' }}>{act.curso}{stats.inscripciones?.length > 1 ? ` · ${act.programa}` : ''}</small>}
                        </td>
                        <td><Badge type={act.tipo} /></td>
                        <td>{act.ponderacion}%</td>
                        <td>{act.fecha_limite}</td>
                        <td>
                          <strong style={{ color: act.dias_restantes < 5 ? 'var(--status-danger-text)' : 'inherit' }}>
                            {act.vencida ? 'Vencida' : `${act.dias_restantes} días`}
                          </strong>
                        </td>
                        <td>
                          {act.estado_entrega === 'APROBADO' ? (
                            <Badge type="APROBADO" text="APROBADA" />
                          ) : act.estado_entrega === 'REQUIERE_CORRECCION' ? (
                          <Badge type="MEDIO" text="CORREGIR" />
                        ) : act.estado_entrega === 'ENTREGADO' ? (
                            <Badge type="BAJO" text="ENTREGADA" />
                          ) : (
                            <Badge type={act.vencida ? 'ALTO' : (act.dias_restantes <= 5 ? 'MEDIO' : 'BAJO')} text={act.vencida ? 'VENCIDA' : 'EN PLAZO'} />
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              stats?.total_postulantes === 0 ? (
                <div>
                  <p style={{ color: 'var(--text-sec)', marginBottom: '12px' }}>
                    Aún no está inscrito en ninguna convocatoria de maestría.
                  </p>
                  <button className="btn btn-primary" onClick={() => onNavigate('enrollment')}>
                    Ir a Inscripción
                  </button>
                </div>
              ) : (
                <p style={{ color: 'var(--text-sec)' }}>No tiene actividades pendientes en este momento.</p>
              )
            )}
          </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', minWidth: 0 }}>
            <div className="card">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <Calendar size={18} color="var(--color-navy)" />
                <span>Calendario</span>
              </h3>
              {(() => {
                const hoy = new Date().toISOString().slice(0, 10);
                const proximos = (stats?.calendario || []).filter((e) => e.fecha.slice(0, 10) >= hoy).slice(0, 8);
                if (proximos.length === 0) return <small>No hay entregas ni sesiones próximas.</small>;
                return (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {proximos.map((e, idx) => (
                      <div key={idx} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                        <div style={{ minWidth: '48px', textAlign: 'center', padding: '6px 4px', borderRadius: '10px', background: e.tipo === 'SESION' ? 'var(--color-sec)' : 'var(--surface-muted)' }}>
                          <div style={{ fontWeight: 700, fontSize: '1.05rem', lineHeight: 1 }}>{e.fecha.slice(8, 10)}</div>
                          <small style={{ fontSize: '0.7rem' }}>{new Date(`${e.fecha.slice(0, 10)}T00:00:00`).toLocaleDateString('es-EC', { month: 'short' })}</small>
                        </div>
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontWeight: 600, fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            {e.tipo === 'SESION' && <Video size={14} />}
                            {e.titulo}
                          </div>
                          <small style={{ color: 'var(--text-sec)', display: 'block' }}>
                            {e.tipo === 'SESION' ? 'Sesión' : 'Entrega'} · {e.fecha.slice(11, 16)} · {e.curso}
                          </small>
                          {e.tipo === 'SESION' && e.url && (
                            <a href={e.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '0.8rem' }}>Entrar a la sesión</a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                );
              })()}
            </div>

            <div className="card">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <AlertTriangle size={18} color="var(--status-warning-text)" />
                <span>Avisos</span>
              </h3>
              {misAlertas.filter((a) => !a.resuelta).length === 0 ? (
                <small>Va al día. No tiene avisos pendientes.</small>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {misAlertas.filter((a) => !a.resuelta).map((a) => (
                    <div key={a.id} style={{ padding: '10px 12px', borderRadius: '12px', border: '1px solid var(--border-light)' }}>
                      <Badge type={a.nivel_riesgo} />
                      <small style={{ display: 'block', marginTop: '6px' }}>{a.motivo_detallado}</small>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h3>Casos Prioritarios en Riesgo Alto</h3>
              <small style={{ color: 'var(--text-sec)' }}>Postulantes que requieren intervención inmediata del tutor o coordinación</small>
            </div>
            <button className="btn btn-outline" onClick={() => onNavigate('applicants')}>
              Ver Todos los Postulantes
            </button>
          </div>

          {stats?.casos_criticos?.length > 0 ? (
            <div className="table-responsive">
              <table className="table">
                <thead>
                  <tr>
                    <th>Postulante</th>
                    <th>Programa</th>
                    <th>Motivo de Clasificación de Riesgo</th>
                    <th>Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.casos_criticos.map((caso) => (
                    <tr key={caso.id}>
                      <td style={{ fontWeight: 600 }}>{caso.nombre}</td>
                      <td><Badge type="PENDIENTE" text={caso.programa} /></td>
                      <td style={{ color: 'var(--status-danger-text)', fontSize: '0.85rem' }}>{caso.motivo}</td>
                      <td>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                          onClick={() => onNavigate('applicants')}
                        >
                          Gestionar Caso
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-sec)' }}>
              <CheckCircle2 size={32} color="var(--status-success-text)" style={{ margin: '0 auto 8px' }} />
              <p>No existen casos clasificados en Riesgo Alto en este momento.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
