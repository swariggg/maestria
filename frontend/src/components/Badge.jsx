import React from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, Clock, Info } from 'lucide-react';

export default function Badge({ type, text }) {
  let badgeClass = 'badge-pending';
  let Icon = Info;

  const upper = (text || type || '').toUpperCase();

  if (['APROBADO', 'BAJO', 'ACTIVO', 'COMPLETADO', 'DOCUMENTACION_COMPLETA', 'RESUELTO'].includes(upper)) {
    badgeClass = 'badge-success';
    Icon = CheckCircle2;
  } else if (['MEDIO', 'EN_PROCESO', 'REQUIERE_CORRECCION', 'DOCUMENTACION_PENDIENTE'].includes(upper)) {
    badgeClass = 'badge-warning';
    Icon = AlertTriangle;
  } else if (['ALTO', 'RECHAZADO', 'REPROBADO', 'ESCALADO', 'BLOQUEADO', 'FALLIDO'].includes(upper)) {
    badgeClass = 'badge-danger';
    Icon = AlertCircle;
  } else if (['PENDIENTE', 'REGISTRADO', 'EN_CURSO', 'PLANIFICADA', 'ABIERTA', 'ENTREGADO'].includes(upper)) {
    badgeClass = 'badge-pending';
    Icon = Clock;
  }

  return (
    <span className={`badge ${badgeClass}`}>
      <Icon size={12} strokeWidth={2.5} />
      {text || type}
    </span>
  );
}
