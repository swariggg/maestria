import React, { useState } from 'react';
import {
  ClipboardList, RefreshCw, UserPlus, PhoneCall, Upload, CheckCircle, FileText, AlertTriangle, Mail
} from 'lucide-react';

const TIPOS = {
  INSCRIPCION: { label: 'Inscripción', icon: ClipboardList },
  ESTADO: { label: 'Estado', icon: RefreshCw },
  TUTOR: { label: 'Tutor', icon: UserPlus },
  SEGUIMIENTO: { label: 'Seguimientos', icon: PhoneCall },
  EVIDENCIA: { label: 'Evidencias', icon: Upload },
  CALIFICACION: { label: 'Calificaciones', icon: CheckCircle },
  DOCUMENTO: { label: 'Documentos', icon: FileText },
  ALERTA: { label: 'Alertas', icon: AlertTriangle },
  CORREO: { label: 'Correos', icon: Mail },
};

/** Línea de tiempo de una inscripción, con filtro por tipo de evento. */
export default function HistoryTimeline({ eventos }) {
  const [filtro, setFiltro] = useState('');
  const presentes = [...new Set(eventos.map((e) => e.tipo))];
  const visibles = filtro ? eventos.filter((e) => e.tipo === filtro) : eventos;

  return (
    <div>
      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '16px' }}>
        <button className={`btn ${filtro === '' ? 'btn-primary' : 'btn-outline'}`} style={{ padding: '5px 12px', fontSize: '0.8rem' }} onClick={() => setFiltro('')}>
          Todo ({eventos.length})
        </button>
        {presentes.map((t) => (
          <button key={t} className={`btn ${filtro === t ? 'btn-primary' : 'btn-outline'}`} style={{ padding: '5px 12px', fontSize: '0.8rem' }} onClick={() => setFiltro(t)}>
            {TIPOS[t]?.label || t} ({eventos.filter((e) => e.tipo === t).length})
          </button>
        ))}
      </div>

      {visibles.length === 0 ? (
        <p style={{ color: 'var(--text-sec)' }}>Sin eventos registrados.</p>
      ) : (
        <div style={{ position: 'relative', paddingLeft: '8px' }}>
          {visibles.map((e, i) => {
            const Icon = TIPOS[e.tipo]?.icon || ClipboardList;
            return (
              <div key={i} style={{ display: 'flex', gap: '12px', paddingBottom: '14px', position: 'relative' }}>
                {i < visibles.length - 1 && (
                  <div style={{ position: 'absolute', left: '15px', top: '32px', bottom: 0, width: '2px', background: 'var(--border-light)' }} />
                )}
                <div className="kpi-icon duo" style={{ width: '32px', height: '32px', flexShrink: 0 }}>
                  <Icon size={15} />
                </div>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', flexWrap: 'wrap' }}>
                    <strong style={{ fontSize: '0.875rem' }}>{e.titulo}</strong>
                    <small style={{ color: 'var(--text-sec)', whiteSpace: 'nowrap' }}>{new Date(e.fecha).toLocaleString()}</small>
                  </div>
                  {e.detalle && <small style={{ display: 'block', color: 'var(--text-sec)' }}>{e.detalle}</small>}
                  {e.actor && <small style={{ display: 'block', color: 'var(--text-sec)' }}>Por: {e.actor}</small>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
