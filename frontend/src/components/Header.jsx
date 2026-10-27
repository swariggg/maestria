import React from 'react';
import { LogOut } from 'lucide-react';
import Badge from './Badge';

function getInitials(name = '') {
  return name
    .replace(/\(.*?\)/g, '')
    .split(' ')
    .filter((word) => word && !word.endsWith('.'))
    .slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join('');
}

export default function Header({ user, onLogout }) {
  return (
    <header className="header">
      <div className="brand">
        <img src="/uide-logo.png" alt="UIDE - Universidad Internacional del Ecuador" className="brand-logo" />
        <div className="brand-divider" />
        <div>
          <small style={{ display: 'block', lineHeight: 1.2 }}>Cursos Preparatorios de Posgrado</small>
          <h2 style={{ fontSize: '1.15rem', margin: 0 }}>APP - Maestría</h2>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
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
