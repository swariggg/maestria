import React, { useState } from 'react';
import { Lock, Mail, ArrowRight } from 'lucide-react';
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

  return (
    <div className="auth-screen">
      <div className="card" style={{ maxWidth: '480px', width: '100%', padding: '36px' }}>
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <img src="/uide-logo.svg" alt="UIDE - Universidad Internacional del Ecuador" style={{ height: '64px', marginBottom: '18px' }} />
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
            border: '1px solid var(--status-danger-border)'
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
      </div>
    </div>
  );
}
