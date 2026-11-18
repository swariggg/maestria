import React, { useEffect, useState } from 'react';
import { LogOut } from 'lucide-react';
import Badge from './Badge';
import NotificationBell from './NotificationBell';
import { api } from '../services/api';

function getInitials(name = '') {
  return name
    .replace(/\(.*?\)/g, '')
    .split(' ')
    .filter((word) => word && !word.endsWith('.'))
    .slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join('');
}

const CERRADAS = ['NO_APROBADO', 'RETIRADO'];

export default function Header({ user, onLogout, onNavigate }) {
  // El postulante pertenece a una sola maestría: se muestra su nombre desde que entra
  const [maestria, setMaestria] = useState(null);
  useEffect(() => {
    if (user?.rol?.codigo !== 'POSTULANTE') return;
    api.getMyEnrollments()
      .then((lista) => {
        const actual = lista.find((i) => !CERRADAS.includes(i.estado_proceso)) || lista[0];
        setMaestria(actual?.programa_nombre || null);
      })
      .catch(() => {});
  }, [user?.id]);

  return (
    <header className="header">
      <div className="brand">
        <img src="/uide-logo.svg" alt="UIDE - Universidad Internacional del Ecuador" className="brand-logo" />
        <div className="brand-divider" />
        <div>
          <small style={{ display: 'block', lineHeight: 1.2 }}>{maestria ? 'Mi maestría' : 'Cursos Preparatorios de Posgrado'}</small>
          <h2 style={{ fontSize: '1.15rem', margin: 0 }}>{maestria || 'APP - Maestría'}</h2>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <NotificationBell onNavigate={onNavigate} />
        <div className="icon-circle" style={{ background: 'var(--color-cream)', color: 'var(--color-burgundy)', fontWeight: 700, fontSize: '0.9rem' }}>
          {getInitials(user?.nombre_completo)}
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: '0.9rem', lineHeight: 1.3 }}>{user?.nombre_completo}</div>
          <div style={{ marginTop: '2px' }}>
            <Badge type={user?.rol?.codigo} text={user?.rol?.nombre} />
          </div>
        </div>

        <button
          onClick={onLogout}
          className="btn btn-outline icon-circle"
          style={{ padding: 0, boxShadow: 'var(--shadow-soft)', border: 'none' }}
          title="Cerrar sesión"
          aria-label="Cerrar sesión"
        >
          <LogOut size={17} />
        </button>
      </div>
    </header>
  );
}
