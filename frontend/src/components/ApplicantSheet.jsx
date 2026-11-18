import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle2, Clock, RotateCcw, XCircle, Lock, Circle, Mail, Phone, Link2 } from 'lucide-react';
import { api } from '../services/api';
import Badge from './Badge';
import { SemaforoPunto } from './Semaforo';

const ESTADOS = {
  PENDIENTE: { label: 'Por entregar', icon: Circle, color: 'var(--color-navy)' },
  POR_CORREGIR: { label: 'Por corregir', icon: RotateCcw, color: 'var(--status-warning-text)' },
  EN_REVISION: { label: 'Entregada, por revisar', icon: Clock, color: 'var(--text-sec)' },
  APROBADA: { label: 'Aprobada', icon: CheckCircle2, color: 'var(--status-success-text)' },
  RECHAZADA: { label: 'Rechazada', icon: XCircle, color: 'var(--status-danger-text)' },
  VENCIDA: { label: 'Vencida sin entregar', icon: AlertTriangle, color: 'var(--status-danger-text)' },
  PROXIMA: { label: 'Aún no abre', icon: Lock, color: 'var(--text-sec)' },
};
const TIPOS = { ASIGNACION: 'Asignación', PRUEBA: 'Prueba', PROYECTO: 'Proyecto', INDIVIDUAL: 'Asignación' };
const fecha = (d) => new Date(d).toLocaleString('es-EC', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });

function textoVence(dias) {
  if (dias < 1) return 'vence hoy';
  if (dias < 2) return 'vence mañana';
  return `vence en ${Math.floor(dias)} días`;
}

/** Seguimiento individual: datos del postulante y sus actividades hechas y por hacer. */
export default function ApplicantSheet({ inscripcionId }) {
  const [ficha, setFicha] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setFicha(null);
    api.getApplicantSheet(inscripcionId).then(setFicha).catch((e) => setError(e.message));
  }, [inscripcionId]);

  if (error) return <div className="notice-danger">{error}</div>;
  if (!ficha) return <div style={{ padding: '20px', textAlign: 'center' }}>Cargando ficha...</div>;

  const p = ficha.postulante;
  const dato = (label, valor) => (
    <div><small style={{ color: 'var(--text-sec)', display: 'block' }}>{label}</small><span>{valor || '—'}</span></div>
  );

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '12px', padding: '14px', borderRadius: '12px', background: 'var(--surface-muted)', fontSize: '0.875rem' }}>
        {dato('Cédula', p.cedula)}
        {dato('Fecha de nacimiento', p.fecha_nacimiento && new Date(`${p.fecha_nacimiento}T00:00`).toLocaleDateString('es-EC'))}
        {dato('Ciudad', p.ciudad)}
        {dato('Título', p.titulo_tercer_nivel)}
        {dato('Universidad', p.universidad_origen)}
        {dato('Contacto de emergencia', p.contacto_emergencia && `${p.contacto_emergencia} ${p.telefono_emergencia || ''}`)}
        <div style={{ gridColumn: '1 / -1', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <span className="btn btn-outline" style={{ padding: '5px 10px', cursor: 'default' }}><Mail size={14} /> <span>{p.email}</span></span>
          {p.telefono && <span className="btn btn-outline" style={{ padding: '5px 10px', cursor: 'default' }}><Phone size={14} /> <span>{p.telefono}</span></span>}
          {p.enlaces.map((e) => (
            <a key={e} className="btn btn-outline" style={{ padding: '5px 10px', textDecoration: 'none' }} href={e} target="_blank" rel="noreferrer"><Link2 size={14} /> <span>{e.replace(/^https?:\/\/(www\.)?/, '').slice(0, 32)}</span></a>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', margin: '14px 0', alignItems: 'center' }}>
        <SemaforoPunto nivel={ficha.nivel_riesgo} />
        <Badge type="APROBADO" text={`${ficha.resumen.hechas} hechas`} />
        <Badge type="PENDIENTE" text={`${ficha.resumen.por_hacer} por hacer`} />
        {ficha.resumen.por_vencer > 0 && <Badge type="ALTO" text={`${ficha.resumen.por_vencer} por vencer`} />}
        {ficha.resumen.vencidas > 0 && <Badge type="RECHAZADO" text={`${ficha.resumen.vencidas} vencidas o rechazadas`} />}
      </div>

      {ficha.cursos.length === 0 && <p style={{ color: 'var(--text-sec)' }}>No tiene cursos asignados a su cargo.</p>}
      {ficha.cursos.map((c) => {
        const acts = ficha.actividades.filter((a) => a.curso_id === c.curso_id);
        return (
          <div key={c.curso_id} style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px', flexWrap: 'wrap', borderBottom: '2px solid var(--border-light)', paddingBottom: '6px' }}>
              <strong>{c.codigo} · {c.nombre}</strong>
              <small style={{ color: 'var(--text-sec)' }}>
                {c.porcentaje}% completado{c.nota_final != null && <> · nota {c.nota_final}/100 (aprueba con {c.nota_minima})</>}
              </small>
            </div>
            {acts.length === 0 && <small style={{ color: 'var(--text-sec)' }}>Sin actividades.</small>}
            {acts.map((a) => {
              const est = ESTADOS[a.estado] || ESTADOS.PENDIENTE;
              const Icono = est.icon;
              return (
                <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '9px 4px', borderBottom: '1px solid var(--border-light)', fontSize: '0.875rem' }}>
                  <Icono size={17} color={est.color} style={{ flexShrink: 0 }} aria-label={est.label} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {a.titulo}
                      {a.vence_pronto && (
                        <span title={`Sin entregar: ${textoVence(a.dias_restantes)}`} style={{ display: 'inline-flex', alignItems: 'center', gap: '3px', color: 'var(--status-danger-text)', fontSize: '0.75rem', fontWeight: 700 }}>
                          <AlertTriangle size={15} /> {textoVence(a.dias_restantes)}
                        </span>
                      )}
                    </div>
                    <small style={{ color: 'var(--text-sec)' }}>
                      {TIPOS[a.tipo] || a.tipo} · {a.ponderacion} pts · hasta {fecha(a.fecha_limite)}
                      {a.fecha_entrega && <> · entregó {fecha(a.fecha_entrega)}{a.entrega_tardia ? ' (tarde)' : ''}</>}
                    </small>
                  </div>
                  <div style={{ textAlign: 'right', fontSize: '0.8rem', color: est.color, fontWeight: 600, whiteSpace: 'nowrap' }}>
                    {est.label}{a.nota != null && <div style={{ color: 'var(--text-main)' }}>{a.nota}/{a.ponderacion}</div>}
                  </div>
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
