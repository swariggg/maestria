import React from 'react';
import { 
  LayoutDashboard, 
  BookOpen, 
  Users, 
  FileCheck, 
  BarChart3, 
  ShieldAlert, 
  History,
  ClipboardList
} from 'lucide-react';

export default function Sidebar({ user, activeTab, setActiveTab }) {
  const role = user?.rol?.codigo;

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['ADMIN', 'COORDINADOR', 'TUTOR', 'POSTULANTE'] },
    { id: 'enrollment', label: 'Inscripción', icon: ClipboardList, roles: ['POSTULANTE'] },
    { id: 'applicants', label: 'Postulantes', icon: Users, roles: ['ADMIN', 'COORDINADOR', 'TUTOR'] },
    { id: 'courses', label: 'Programas y Cursos', icon: BookOpen, roles: ['ADMIN', 'COORDINADOR', 'POSTULANTE'] },
    { id: 'evidences', label: 'Evidencias', icon: FileCheck, roles: ['ADMIN', 'COORDINADOR', 'TUTOR', 'POSTULANTE'] },
    { id: 'reports', label: 'Reportes y Matrices', icon: BarChart3, roles: ['ADMIN', 'COORDINADOR', 'TUTOR', 'POSTULANTE'] },
    { id: 'audit', label: 'Auditoría Global', icon: History, roles: ['ADMIN', 'COORDINADOR'] },
  ];

  const visibleItems = navItems.filter(item => item.roles.includes(role));

  return (
    <nav className="topnav" aria-label="Navegación principal">
      {visibleItems.map((item) => {
        const Icon = item.icon;
        const isActive = activeTab === item.id;
        return (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`nav-link duo ${isActive ? 'active' : ''}`}
          >
            <Icon size={18} />
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
