import React, { useState } from 'react';
import { GraduationCap, Lock, Mail, ArrowRight, ShieldCheck, UserCheck } from 'lucide-react';
import { api } from '../services/api';

export default function LoginPage({ onLoginSuccess, onShowRegister }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const data = await api.login({ email, password });
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      onLoginSuccess(data.user);
    } catch (err) {
      setError(err.message || 'Error al iniciar sesión.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (demoEmail) => {
    setEmail(demoEmail);
    setPassword('Demo2026!');
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
      background: 'linear-gradient(135deg, #DCE7FF 0%, #F8C7DE 100%)'
    }}>
      <div className="card" style={{ maxWidth: '480px', width: '100%', padding: '36px' }}>
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div style={{
            display: 'inline-flex',
            background: 'var(--color-primary)',
            padding: '14px',
            borderRadius: '20px',
            boxShadow: '0 4px 15px rgba(248, 199, 222, 0.5)',
            marginBottom: '16px'
          }}>
            <GraduationCap size={36} color="#701A48" />
          </div>
          <h1>APP - Maestría</h1>
          <p style={{ color: 'var(--text-sec)', marginTop: '4px' }}>
            Universidad Internacional del Ecuador (UIDE)
          </p>
          <small style={{ color: 'var(--text-sec)' }}>Gestión Académica de Cursos Preparatorios</small>
        </div>

        {error && (
          <div style={{
            background: 'var(--status-danger-bg)',
            color: 'var(--status-danger-text)',
            padding: '12px 16px',
            borderRadius: '12px',
            marginBottom: '20px',
            fontSize: '0.875rem',
            border: '1px solid #FECACA'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Correo Electrónico Institucional</label>
            <div style={{ position: 'relative' }}>
              <input
                type="email"
                className="form-input"
                style={{ paddingLeft: '40px' }}
                placeholder="usuario@uide.edu.ec"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <Mail size={18} color="var(--text-sec)" style={{ position: 'absolute', left: '12px', top: '12px' }} />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Contraseña</label>
            <div style={{ position: 'relative' }}>
              <input
                type="password"
                className="form-input"
                style={{ paddingLeft: '40px' }}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <Lock size={18} color="var(--text-sec)" style={{ position: 'absolute', left: '12px', top: '12px' }} />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: '8px', padding: '12px' }}
            disabled={loading}
          >
            {loading ? 'Validando credenciales...' : 'Iniciar Sesión'}
            <ArrowRight size={18} />
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: '16px', fontSize: '0.9rem', color: 'var(--text-sec)' }}>
          ¿Es postulante y aún no tiene cuenta?{' '}
          <button
            type="button"
            onClick={onShowRegister}
            style={{ background: 'none', border: 'none', padding: 0, color: 'var(--text-main)', fontWeight: 600, textDecoration: 'underline', cursor: 'pointer' }}
          >
            Crear cuenta
          </button>
        </p>

        {/* Cuentas de Demostración para Pruebas Inmediatas */}
        <div style={{ marginTop: '32px', paddingTop: '24px', borderTop: '1px solid var(--border-light)' }}>
          <small style={{ display: 'block', fontWeight: 600, color: 'var(--text-sec)', marginBottom: '10px' }}>
            ACCESO RÁPIDO PARA EVALUACIÓN (DEMO):
          </small>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            <button
              type="button"
              onClick={() => handleQuickLogin('admin@uide.edu.ec')}
              className="btn btn-outline"
              style={{ padding: '6px 10px', fontSize: '0.775rem' }}
            >
              👑 Administrador
            </button>
            <button
              type="button"
              onClick={() => handleQuickLogin('coordinador.ia@uide.edu.ec')}
              className="btn btn-outline"
              style={{ padding: '6px 10px', fontSize: '0.775rem' }}
            >
              🎓 Coordinador IA
            </button>
            <button
              type="button"
              onClick={() => handleQuickLogin('tutor.ia@uide.edu.ec')}
              className="btn btn-outline"
              style={{ padding: '6px 10px', fontSize: '0.775rem' }}
            >
              👨‍🏫 Tutor IA
            </button>
            <button
              type="button"
              onClick={() => handleQuickLogin('postulante.perez@uide.edu.ec')}
              className="btn btn-outline"
              style={{ padding: '6px 10px', fontSize: '0.775rem' }}
            >
              🟢 Postulante Pérez (Bajo Riesgo)
            </button>
            <button
              type="button"
              onClick={() => handleQuickLogin('postulante.zambrano@uide.edu.ec')}
              className="btn btn-outline"
              style={{ padding: '6px 10px', fontSize: '0.775rem' }}
            >
              🔴 Postulante Zambrano (Alto Riesgo)
            </button>
          </div>
          <small style={{ display: 'block', color: 'var(--text-sec)', marginTop: '8px', fontSize: '0.75rem' }}>
            Contraseña universal de prueba: <code>Demo2026!</code>
          </small>
        </div>
      </div>
    </div>
  );
}
