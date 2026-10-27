import React from 'react';
import { 
  LayoutDashboard, 
  BookOpen, 
  Users, 
  FileCheck, 
  BarChart3, 
  ShieldAlert, 
  History 
} from 'lucide-react';

export default function Sidebar({ user, activeTab, setActiveTab }) {
  const role = user?.rol?.codigo;

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['ADMIN', 'COORDINADOR', 'TUTOR', 'POSTULANTE'] },
    { id: 'applicants', label: 'Postulantes', icon: Users, roles: ['ADMIN', 'COORDINADOR', 'TUTOR'] },
    { id: 'courses', label: 'Programas y Cursos', icon: BookOpen, roles: ['ADMIN', 'COORDINADOR', 'POSTULANTE'] },
    { id: 'evidences', label: 'Evidencias', icon: FileCheck, roles: ['ADMIN', 'COORDINADOR', 'TUTOR', 'POSTULANTE'] },
    { id: 'reports', label: 'Reportes y Matrices', icon: BarChart3, roles: ['ADMIN', 'COORDINADOR', 'TUTOR', 'POSTULANTE'] },
    { id: 'audit', label: 'Auditoría Global', icon: History, roles: ['ADMIN', 'COORDINADOR'] },
  ];

  const visibleItems = navItems.filter(item => item.roles.includes(role));

  return (
    <aside className="sidebar">
      <div style={{ padding: '24px 20px', borderBottom: '1px solid var(--border-light)' }}>
        <small style={{ textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-sec)', fontWeight: 600 }}>
          Navegación Principal
        </small>
      </div>

      <nav style={{ padding: '12px 0', flex: 1 }}>
        {visibleItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`nav-link ${isActive ? 'active' : ''}`}
              style={{
                width: 'calc(100% - 24px)',
                textAlign: 'left',
                border: 'none',
                cursor: 'pointer',
                background: isActive ? 'var(--color-sec)' : 'transparent'
              }}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div style={{ padding: '20px', borderTop: '1px solid var(--border-light)', backgroundColor: 'var(--surface-muted)' }}>
        <small style={{ display: 'block', color: 'var(--text-sec)' }}>Versión 1.0.0</small>
        <small style={{ color: 'var(--text-sec)', fontSize: '0.75rem' }}>UIDE Posgrados 2026</small>
      </div>
    </aside>
  );
}
