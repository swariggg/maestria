import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ApplicantsPage from './pages/ApplicantsPage';
import CoursesPage from './pages/CoursesPage';
import EvidencesPage from './pages/EvidencesPage';
import ReportsPage from './pages/ReportsPage';
import AuditPage from './pages/AuditPage';
import AlertsPage from './pages/AlertsPage';
import ProfilePage from './pages/ProfilePage';
import ConfigPage from './pages/ConfigPage';
import UsersPage from './pages/UsersPage';
import RegisterPage from './pages/RegisterPage';
import EnrollmentPage from './pages/EnrollmentPage';
import ChangePasswordPage from './pages/ChangePasswordPage';
import CertificatesPage from './pages/CertificatesPage';
import { api } from './services/api';

export default function App() {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(true);
  const [showRegister, setShowRegister] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      const storedUser = localStorage.getItem('user');
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
        } catch {
          localStorage.removeItem('user');
        }
      }

      // Validar sesión contra el backend
      try {
        const me = await api.getMe();
        setUser(me);
        localStorage.setItem('user', JSON.stringify(me));
      } catch {
        setUser(null);
        localStorage.removeItem('user');
        localStorage.removeItem('access_token');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch (err) {
      console.error(err);
    } finally {
      localStorage.removeItem('user');
      localStorage.removeItem('access_token');
      setUser(null);
      setActiveTab('dashboard');
    }
  };

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-main)'
      }}>
        <div style={{ textAlign: 'center' }}>
          <h2 style={{ color: 'var(--text-main)' }}>Cargando Sistema APP - Maestría...</h2>
          <small style={{ color: 'var(--text-sec)' }}>Universidad Internacional del Ecuador</small>
        </div>
      </div>
    );
  }

  if (!user) {
    if (showRegister) {
      return (
        <RegisterPage
          onRegistered={(newUser) => {
            setShowRegister(false);
            setUser(newUser);
            setActiveTab('enrollment');
          }}
          onBack={() => setShowRegister(false)}
        />
      );
    }
    return (
      <LoginPage
        onLoginSuccess={(loggedInUser) => setUser(loggedInUser)}
        onShowRegister={() => setShowRegister(true)}
      />
    );
  }

  // Cuenta creada o restablecida por el administrador: primero cambia la contraseña
  if (user.debe_cambiar_password) {
    return (
      <ChangePasswordPage
        user={user}
        onChanged={() => {
          const actualizado = { ...user, debe_cambiar_password: false };
          localStorage.setItem('user', JSON.stringify(actualizado));
          setUser(actualizado);
        }}
        onLogout={handleLogout}
      />
    );
  }

  return (
    <div className="app-container">
      <div className="topbar">
        <Header user={user} onLogout={handleLogout} />
        <Sidebar user={user} activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>
      <main className="page-body">
        {activeTab === 'dashboard' && <DashboardPage user={user} onNavigate={setActiveTab} />}
        {activeTab === 'enrollment' && <EnrollmentPage />}
        {activeTab === 'applicants' && <ApplicantsPage user={user} />}
        {activeTab === 'courses' && <CoursesPage user={user} />}
        {activeTab === 'evidences' && <EvidencesPage user={user} />}
        {activeTab === 'certificates' && <CertificatesPage user={user} />}
        {activeTab === 'reports' && <ReportsPage user={user} />}
        {activeTab === 'profile' && <ProfilePage />}
        {activeTab === 'alerts' && <AlertsPage user={user} />}
        {activeTab === 'config' && <ConfigPage />}
        {activeTab === 'users' && <UsersPage user={user} />}
        {activeTab === 'audit' && <AuditPage user={user} />}
      </main>
    </div>
  );
}
