import React, { useLayoutEffect, useRef, useState } from 'react';
import { 
  LayoutDashboard, 
  BookOpen, 
  Users, 
  FileCheck, 
  BarChart3, 
  ShieldAlert, 
  History,
  ClipboardList,
  UserRound,
  SlidersHorizontal,
  UserCog,
  Award
} from 'lucide-react';

export default function Sidebar({ user, activeTab, setActiveTab }) {
  const role = user?.rol?.codigo;

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['ADMIN', 'COORDINADOR', 'TUTOR', 'POSTULANTE'] },
    { id: 'enrollment', label: 'Inscripción', icon: ClipboardList, roles: ['POSTULANTE'] },
    { id: 'profile', label: 'Mi Perfil', icon: UserRound, roles: ['POSTULANTE'] },
    { id: 'applicants', label: 'Postulantes', icon: Users, roles: ['ADMIN', 'COORDINADOR', 'TUTOR'] },
    { id: 'courses', label: 'Programas y Cursos', icon: BookOpen, roles: ['ADMIN', 'COORDINADOR', 'TUTOR', 'POSTULANTE'] },
    { id: 'alerts', label: 'Alertas', icon: ShieldAlert, roles: ['ADMIN', 'COORDINADOR', 'TUTOR'] },
    { id: 'evidences', label: 'Evidencias', icon: FileCheck, roles: ['ADMIN', 'COORDINADOR', 'TUTOR', 'POSTULANTE'] },
    { id: 'certificates', label: 'Certificados', icon: Award, roles: ['ADMIN', 'COORDINADOR', 'TUTOR', 'POSTULANTE'] },
    { id: 'reports', label: 'Reportes y Matrices', icon: BarChart3, roles: ['ADMIN', 'COORDINADOR', 'TUTOR', 'POSTULANTE'] },
    { id: 'users', label: 'Usuarios', icon: UserCog, roles: ['ADMIN'] },
    { id: 'config', label: 'Configuración', icon: SlidersHorizontal, roles: ['ADMIN'] },
    { id: 'audit', label: 'Auditoría Global', icon: History, roles: ['ADMIN'] },
  ];

  const visibleItems = navItems.filter(item => item.roles.includes(role));

  // Píldora que se desliza hasta la opción activa
  const navRef = useRef(null);
  const [pill, setPill] = useState(null);
  useLayoutEffect(() => {
    const medir = () => {
      const activo = navRef.current?.querySelector('.nav-link.active');
      if (!activo) return setPill(null);
      setPill({ x: activo.offsetLeft, y: activo.offsetTop, w: activo.offsetWidth, h: activo.offsetHeight });
    };
    medir();
    document.fonts?.ready.then(medir);
    window.addEventListener('resize', medir);
    return () => window.removeEventListener('resize', medir);
  }, [activeTab, role]);

  return (
    <nav className="topnav" aria-label="Navegación principal" ref={navRef}>
      {pill && (
        <span
          className="nav-pill"
          aria-hidden="true"
          style={{ transform: `translate(${pill.x}px, ${pill.y}px)`, width: pill.w, height: pill.h }}
        />
      )}
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
