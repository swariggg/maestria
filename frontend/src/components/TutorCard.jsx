import React, { useState, useEffect } from 'react';
import { Mail, MessageSquare, Clock, Phone } from 'lucide-react';
import { api } from '../services/api';
import ProfilePhoto from './ProfilePhoto';

/** Enlace para abrir un chat de Teams con la cuenta del tutor (solo es un enlace, la app no se conecta a Teams). */
export function enlaceTeams(usuario) {
  if (!usuario) return null;
  if (/^https?:\/\//i.test(usuario)) return usuario;
  return `https://teams.microsoft.com/l/chat/0/0?users=${encodeURIComponent(usuario)}`;
}

/** Tarjeta del tutor en la portada del curso, con su foto y cómo contactarlo. */
export function TutorContact({ tutor }) {
  const correo = tutor.correo_outlook || tutor.email;
  const teams = enlaceTeams(tutor.usuario_teams);
  return (
    <div style={{ display: 'flex', gap: '18px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
      <ProfilePhoto usuarioId={tutor.usuario_id} nombre={tutor.nombre_completo} tieneFoto={tutor.tiene_foto} size={84} />
      <div style={{ flex: '1 1 240px', minWidth: 0 }}>
        <small style={{ color: 'var(--text-sec)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>Su tutor(a)</small>
        <h3 style={{ margin: '2px 0 2px' }}>{tutor.nombre_completo}</h3>
        {tutor.especialidad && <div style={{ color: 'var(--color-uide)', fontWeight: 600, fontSize: '0.9rem' }}>{tutor.especialidad}</div>}
        {tutor.presentacion && <p style={{ margin: '10px 0 0', fontSize: '0.9rem', color: 'var(--text-main)', whiteSpace: 'pre-line' }}>{tutor.presentacion}</p>}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '14px' }}>
          {correo && (
            <a className="btn btn-outline" style={{ padding: '6px 12px', textDecoration: 'none' }} href={`mailto:${correo}`}>
              <Mail size={15} /> <span>{correo}</span>
            </a>
          )}
          {teams && (
            <a className="btn btn-outline" style={{ padding: '6px 12px', textDecoration: 'none' }} href={teams} target="_blank" rel="noreferrer">
              <MessageSquare size={15} /> <span>Escribir por Teams</span>
            </a>
          )}
          {tutor.telefono && (
            <span className="btn btn-outline" style={{ padding: '6px 12px', cursor: 'default' }}>
              <Phone size={15} /> <span>{tutor.telefono}</span>
            </span>
          )}
        </div>
        {tutor.horario_atencion && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '10px', fontSize: '0.85rem', color: 'var(--text-sec)' }}>
            <Clock size={14} /> <span>Atención: {tutor.horario_atencion}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function TutorCard({ cursoId }) {
  const [tutor, setTutor] = useState(undefined);

  useEffect(() => {
    let vivo = true;
    setTutor(undefined);
    api.getCourseTutor(cursoId).then((t) => vivo && setTutor(t || null)).catch(() => vivo && setTutor(null));
    return () => { vivo = false; };
  }, [cursoId]);

  if (tutor === undefined) return null;
  return (
    <div className="card" style={{ margin: '24px 0', borderLeft: '4px solid var(--color-uide)' }}>
      {tutor ? <TutorContact tutor={tutor} /> : (
        <p style={{ margin: 0, color: 'var(--text-sec)' }}>Este curso todavía no tiene tutor asignado.</p>
      )}
    </div>
  );
}
