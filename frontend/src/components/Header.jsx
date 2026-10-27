import React from 'react';
import { LogOut, GraduationCap, Shield, User } from 'lucide-react';
import Badge from './Badge';

export default function Header({ user, onLogout }) {
  return (
    <header className="header">
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ 
          background: 'var(--color-primary)', 
          padding: '8px', 
          borderRadius: '12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 2px 8px rgba(248, 199, 222, 0.4)'
        }}>
          <GraduationCap size={24} color="#701A48" />
        </div>
        <div>
          <h2 style={{ fontSize: '1.15rem', margin: 0, color: 'var(--text-main)' }}>APP - Maestría</h2>
          <small style={{ color: 'var(--text-sec)' }}>Universidad Internacional del Ecuador (UIDE)</small>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontWeight: 600, fontSize: '0.925rem' }}>{user?.nombre_completo}</div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '2px' }}>
            <Badge type={user?.rol?.codigo} text={user?.rol?.nombre} />
          </div>
        </div>

        <button 
          onClick={onLogout} 
          className="btn btn-outline" 
          style={{ padding: '8px 14px', fontSize: '0.875rem' }}
          title="Cerrar Sesión Segura"
        >
          <LogOut size={16} />
          <span>Salir</span>
        </button>
      </div>
    </header>
  );
}
