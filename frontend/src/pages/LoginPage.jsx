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
    <div className="login-screen">
      <div className="login-shell">
        <section className="login-intro">
          <img src="/uide-logo.svg" alt="UIDE - Universidad Internacional del Ecuador" className="login-logo" />

          <h1 className="login-headline">
            Reinventemos
            <span className="lh-inline">
              el futuro <span className="lh-badge">Posgrado UIDE</span>
            </span>
            de tu carrera
          </h1>
          <p className="login-lead">
            Gestión académica de los cursos preparatorios: inscripción, actividades, evidencias,
            seguimiento y certificados, con avisos dentro de la app.
          </p>
        </section>

        <section className="login-form-card">
          <h2>Iniciar sesión</h2>
          <small style={{ display: 'block', marginBottom: '20px' }}>Gestión Académica de Cursos Preparatorios</small>

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
        </section>

        <aside className="login-media" aria-hidden="true">
          <img src="/campus-uide-2.jpg" alt="" style={{ objectPosition: "66% center" }} />
          <div className="login-media-glass">
            <span className="lmg-big">Campus<br />Quito</span>
            <span className="lmg-sep" />
            <span className="lmg-small">Universidad<br />Internacional<br />del Ecuador</span>
          </div>
        </aside>
      </div>
    </div>
  );
}
