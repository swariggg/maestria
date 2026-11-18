import React, { useState, useEffect, useMemo } from 'react';
import {
  KanbanSquare, CalendarDays, AlertTriangle, CheckCircle2, Clock, RotateCcw, XCircle, Lock, Circle, ChevronLeft, ChevronRight, Upload,
} from 'lucide-react';
import { api } from '../services/api';
import './BoardPage.css';

// Colores de la marca UIDE para distinguir cada curso
const COLORES = [
  { color: '#910048', tinte: '#F7E6EE' },
  { color: '#002D72', tinte: '#E6ECF5' },
  { color: '#B07F00', tinte: '#FDF5DC' },
  { color: '#5B2C6F', tinte: '#F1E9F5' },
  { color: '#00737A', tinte: '#E3F3F4' },
];

const ESTADOS = {
  PENDIENTE: { label: 'Por entregar', icon: Circle, color: 'var(--color-navy)' },
  POR_CORREGIR: { label: 'Por corregir', icon: RotateCcw, color: 'var(--status-warning-text)' },
  EN_REVISION: { label: 'Entregada, en revisión', icon: Clock, color: 'var(--text-sec)' },
  APROBADA: { label: 'Aprobada', icon: CheckCircle2, color: 'var(--status-success-text)' },
  RECHAZADA: { label: 'Rechazada', icon: XCircle, color: 'var(--status-danger-text)' },
  VENCIDA: { label: 'Vencida sin entregar', icon: AlertTriangle, color: 'var(--status-danger-text)' },
  PROXIMA: { label: 'Aún no abre', icon: Lock, color: 'var(--text-sec)' },
};
const COLUMNAS_ESTADO = ['PENDIENTE', 'POR_CORREGIR', 'EN_REVISION', 'APROBADA', 'VENCIDA'];
const TIPOS = { ASIGNACION: 'Asignación', PRUEBA: 'Prueba', PROYECTO: 'Proyecto', INDIVIDUAL: 'Asignación' };

const inicioDia = (d) => { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; };
const inicioSemana = (d) => { const x = inicioDia(d); const dia = (x.getDay() + 6) % 7; x.setDate(x.getDate() - dia); return x; };
const DIA_MS = 86400000;
const fechaLarga = (d) => d.toLocaleDateString('es-EC', { day: 'numeric', month: 'long' });
const fechaCorta = (d) => d.toLocaleDateString('es-EC', { day: 'numeric', month: 'short' });
const hora = (d) => d.toLocaleTimeString('es-EC', { hour: '2-digit', minute: '2-digit' });

function etiquetaDia(d, hoy) {
  const dif = Math.round((inicioDia(d) - inicioDia(hoy)) / DIA_MS);
  if (dif === 0) return ['Hoy', fechaLarga(d)];
  if (dif === 1) return ['Mañana', fechaLarga(d)];
  if (dif === -1) return ['Ayer', fechaLarga(d)];
  const dia = d.toLocaleDateString('es-EC', { weekday: 'long' });
  return [dia.charAt(0).toUpperCase() + dia.slice(1), fechaLarga(d)];
}

function textoVence(a) {
  if (a.dias_restantes < 0) return 'Venció';
  if (a.dias_restantes < 1) return 'Vence hoy';
  if (a.dias_restantes < 2) return 'Vence mañana';
  return `Vence en ${Math.floor(a.dias_restantes)} días`;
}

/** Anillos concéntricos: uno por curso, con el avance total en el centro. */
function Anillos({ cursos, colorDe, porcentaje, aprobadas, total }) {
  const size = 230;
  const grosor = Math.max(8, Math.min(16, 70 / Math.max(cursos.length, 1)));
  const separacion = 4;
  return (
    <svg width="100%" viewBox={`0 0 ${size} ${size}`} style={{ maxWidth: size, display: 'block', margin: '0 auto' }} role="img"
      aria-label={`Avance total ${porcentaje}%`}>
      {cursos.map((c, i) => {
        const r = size / 2 - grosor / 2 - i * (grosor + separacion) - 2;
        if (r <= grosor) return null;
        const largo = 2 * Math.PI * r;
        const { color, tinte } = colorDe(c.curso_id);
        return (
          <g key={c.curso_id} transform={`rotate(-90 ${size / 2} ${size / 2})`}>
            <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={tinte} strokeWidth={grosor} />
            <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={grosor} strokeLinecap="round"
              strokeDasharray={`${(largo * c.porcentaje) / 100} ${largo}`}>
              <title>{`${c.nombre}: ${c.porcentaje}%`}</title>
            </circle>
          </g>
        );
      })}
      <text x="50%" y="48%" textAnchor="middle" fontSize="30" fontWeight="700" fill="var(--color-uide)">{Math.round(porcentaje)}%</text>
      <text x="50%" y="60%" textAnchor="middle" fontSize="13" fill="var(--text-sec)">{aprobadas}/{total} aprobadas</text>
    </svg>
  );
}

export default function BoardPage({ onNavigate }) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [vista, setVista] = useState(() => { try { return localStorage.getItem('vista_tablero') || 'tablero'; } catch { return 'tablero'; } });
  const [agrupar, setAgrupar] = useState('curso');
  const [semana, setSemana] = useState(() => inicioSemana(new Date()));

  useEffect(() => {
    api.getBoard().then(setDatos).catch((e) => setError(e.message));
  }, []);

  const cambiarVista = (v) => { setVista(v); try { localStorage.setItem('vista_tablero', v); } catch { /* sin almacenamiento */ } };

  const colorDe = useMemo(() => {
    const mapa = {};
    (datos?.cursos || []).forEach((c, i) => { mapa[c.curso_id] = COLORES[i % COLORES.length]; });
    return (id) => mapa[id] || COLORES[0];
  }, [datos]);
  const cursoDe = (id) => datos.cursos.find((c) => c.curso_id === id) || {};

  if (error) return <div className="notice-danger">{error}</div>;
  if (!datos) return <div style={{ textAlign: 'center', padding: '60px' }}>Cargando sus actividades...</div>;

  const hoy = new Date(datos.hoy);
  const irAEntregar = () => onNavigate && onNavigate('evidences');

  const Tarjeta = ({ a }) => {
    const est = ESTADOS[a.estado] || ESTADOS.PENDIENTE;
    const Icono = est.icon;
    const limite = new Date(a.fecha_limite);
    return (
      <button type="button" className="kanban-card" style={{ '--card-color': colorDe(a.curso_id).color }} onClick={irAEntregar}
        title="Ir a Evidencias para entregar o ver la calificación">
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
          <span className="kc-title">{a.titulo}</span>
          {a.vence_pronto && <AlertTriangle size={17} color="var(--status-danger-text)" aria-label="Vence pronto" style={{ flexShrink: 0 }} />}
        </div>
        <div className="kc-meta">
          {agrupar === 'estado' && <>{cursoDe(a.curso_id).codigo} · </>}{TIPOS[a.tipo] || a.tipo} · {a.ponderacion} pts{a.nota != null && <> · nota {a.nota}</>}
        </div>
        <div className="kc-meta">Entrega hasta: {fechaCorta(limite)}, {hora(limite)}</div>
        {a.fecha_entrega && (
          <div className="kc-meta">
            Entregó el {fechaCorta(new Date(a.fecha_entrega))} a las {hora(new Date(a.fecha_entrega))}{a.entrega_tardia ? ' (tarde)' : ''}
          </div>
        )}
        <div className="kc-flag" style={{ color: a.vence_pronto ? 'var(--status-danger-text)' : est.color }}>
          <Icono size={13} /> {a.vence_pronto ? textoVence(a) : est.label}
          {a.intentos_usados > 0 && a.estado !== 'APROBADA' && <span style={{ fontWeight: 500, textTransform: 'none' }}>· intento {a.intentos_usados}/{a.max_reenvios}</span>}
        </div>
      </button>
    );
  };

  // ---------- Tablero ----------
  const columnas = agrupar === 'curso'
    ? datos.cursos.map((c) => ({
      clave: c.curso_id, titulo: c.nombre, sub: `${c.codigo} · ${c.porcentaje}% completado`, color: colorDe(c.curso_id).color, porcentaje: c.porcentaje,
      // Primero lo que hay que hacer, luego lo demás
      items: datos.actividades.filter((a) => a.curso_id === c.curso_id)
        .sort((x, y) => (['APROBADA', 'EN_REVISION'].includes(x.estado) - ['APROBADA', 'EN_REVISION'].includes(y.estado)) || (new Date(x.fecha_limite) - new Date(y.fecha_limite))),
    }))
    : COLUMNAS_ESTADO.map((e) => ({
      clave: e, titulo: ESTADOS[e].label, color: ESTADOS[e].color,
      items: datos.actividades.filter((a) => a.estado === e || (e === 'PENDIENTE' && a.estado === 'PROXIMA') || (e === 'VENCIDA' && a.estado === 'RECHAZADA')),
    })).map((c) => ({ ...c, sub: `${c.items.length} actividad(es)` }));

  // ---------- Agenda ----------
  const finSemana = new Date(semana.getTime() + 7 * DIA_MS);
  const deLaSemana = datos.actividades.filter((a) => { const f = new Date(a.fecha_limite); return f >= semana && f < finSemana; });
  const dias = [];
  deLaSemana.forEach((a) => {
    const clave = inicioDia(new Date(a.fecha_limite)).getTime();
    let d = dias.find((x) => x.clave === clave);
    if (!d) { d = { clave, items: [] }; dias.push(d); }
    d.items.push(a);
  });
  dias.sort((x, y) => x.clave - y.clave);
  const proximas = datos.actividades.filter((a) => ['PENDIENTE', 'POR_CORREGIR'].includes(a.estado) && a.dias_restantes >= 0 && a.dias_restantes <= 7)
    .sort((x, y) => x.dias_restantes - y.dias_restantes);
  const grupos = [];
  proximas.forEach((a) => {
    const t = textoVence(a);
    let g = grupos.find((x) => x.t === t);
    if (!g) { g = { t, items: [] }; grupos.push(g); }
    g.items.push(a);
  });

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <h1>Mis actividades</h1>
        <p style={{ color: 'var(--text-sec)' }}>
          {datos.resumen.pendientes} por hacer · {datos.resumen.aprobadas} de {datos.resumen.total} aprobadas
          {datos.resumen.vencen_pronto > 0 && <> · <strong style={{ color: 'var(--status-danger-text)' }}>{datos.resumen.vencen_pronto} vence(n) en {datos.dias_alerta} días o menos</strong></>}
        </p>
      </div>

      <div className="board-toolbar">
        <div className="board-switch" role="tablist">
          <button type="button" className={vista === 'tablero' ? 'on' : ''} onClick={() => cambiarVista('tablero')}><KanbanSquare size={15} /> Tablero</button>
          <button type="button" className={vista === 'agenda' ? 'on' : ''} onClick={() => cambiarVista('agenda')}><CalendarDays size={15} /> Agenda y avance</button>
        </div>
        {vista === 'tablero' && (
          <div className="board-switch">
            <button type="button" className={agrupar === 'curso' ? 'on' : ''} onClick={() => setAgrupar('curso')}>Por curso</button>
            <button type="button" className={agrupar === 'estado' ? 'on' : ''} onClick={() => setAgrupar('estado')}>Por estado</button>
          </div>
        )}
        <button type="button" className="btn btn-primary" onClick={irAEntregar}><Upload size={15} /> <span>Entregar una actividad</span></button>
      </div>

      {datos.cursos.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', color: 'var(--text-sec)' }}>Cuando se inscriba en una convocatoria, aquí verá sus cursos y actividades.</div>
      ) : vista === 'tablero' ? (
        <div className="kanban">
          {columnas.map((col) => (
            <div key={col.clave} className="kanban-col" style={{ '--col-color': col.color }}>
              <div className="kanban-col-head">
                <strong>{col.titulo} ({col.items.length})</strong>
                <small>{col.sub}</small>
                {col.porcentaje != null && <div className="kanban-bar"><span style={{ width: `${col.porcentaje}%` }} /></div>}
              </div>
              {col.items.length === 0 ? <div className="kanban-empty">Sin actividades</div> : col.items.map((a) => <Tarjeta key={`${a.inscripcion_id}-${a.id}`} a={a} />)}
            </div>
          ))}
        </div>
      ) : (
        <div className="agenda">
          <div>
            <div className="agenda-week">
              <button type="button" aria-label="Semana anterior" onClick={() => setSemana(new Date(semana.getTime() - 7 * DIA_MS))}><ChevronLeft size={16} /></button>
              <strong>{fechaCorta(semana)} – {fechaCorta(new Date(finSemana.getTime() - DIA_MS))}</strong>
              <button type="button" aria-label="Semana siguiente" onClick={() => setSemana(new Date(semana.getTime() + 7 * DIA_MS))}><ChevronRight size={16} /></button>
            </div>
            {dias.length === 0 && <div className="card" style={{ textAlign: 'center', color: 'var(--text-sec)' }}>No tiene entregas esta semana.</div>}
            {dias.map((d) => {
              const [titulo, sub] = etiquetaDia(new Date(d.clave), hoy);
              return (
                <div className="agenda-day" key={d.clave}>
                  <h3>{titulo}{titulo !== sub && <small>{sub}</small>}</h3>
                  {d.items.map((a) => {
                    const c = cursoDe(a.curso_id);
                    const { color, tinte } = colorDe(a.curso_id);
                    const est = ESTADOS[a.estado] || ESTADOS.PENDIENTE;
                    const Icono = est.icon;
                    return (
                      <button type="button" key={`${a.inscripcion_id}-${a.id}`} className="agenda-item" style={{ '--item-color': color, '--item-tint': tinte }} onClick={irAEntregar}>
                        <span className="agenda-course">{c.nombre}</span>
                        <Icono size={20} color={est.color} aria-label={est.label} />
                        <span style={{ minWidth: 0 }}>
                          <span className="ai-sub">{c.codigo} · {TIPOS[a.tipo] || a.tipo}{a.vence_pronto && <span style={{ color: 'var(--status-danger-text)', fontWeight: 700 }}> · {textoVence(a)}</span>}</span>
                          <span className="ai-title" style={{ display: 'block' }}>{a.titulo}</span>
                          {a.fecha_entrega && <small style={{ color: 'var(--text-sec)' }}>Entregó el {fechaCorta(new Date(a.fecha_entrega))} a las {hora(new Date(a.fecha_entrega))} · {est.label}</small>}
                        </span>
                        <span className="ai-right">
                          <strong>{a.ponderacion}</strong> PTS<br />
                          Fecha de entrega: {hora(new Date(a.fecha_limite))}
                        </span>
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>

          <div className="card">
            <h3 style={{ marginBottom: '10px' }}>Mi avance</h3>
            <Anillos cursos={datos.cursos} colorDe={colorDe} porcentaje={datos.resumen.porcentaje} aprobadas={datos.resumen.aprobadas} total={datos.resumen.total} />
            <div className="ring-legend">
              {datos.cursos.map((c) => (
                <span key={c.curso_id}><i style={{ background: colorDe(c.curso_id).color }} />{c.codigo} {c.porcentaje}%</span>
              ))}
            </div>
            {grupos.length === 0 ? (
              <small style={{ color: 'var(--text-sec)' }}>Nada vence en los próximos 7 días.</small>
            ) : grupos.map((g) => (
              <div className="due-group" key={g.t}>
                <small>{g.t}</small>
                {g.items.map((a) => {
                  const { color, tinte } = colorDe(a.curso_id);
                  return (
                    <div className="due-card" key={`${a.inscripcion_id}-${a.id}`} style={{ '--item-color': color, '--item-tint': tinte }}>
                      <div className="dc-course">{cursoDe(a.curso_id).nombre}</div>
                      <div className="dc-title">{a.titulo}</div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>Hasta {fechaCorta(new Date(a.fecha_limite))}, {hora(new Date(a.fecha_limite))}</span>
                        <strong>{a.ponderacion} pts</strong>
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
