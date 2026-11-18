import React, { useState } from 'react';
import { Lock, Mail, ArrowRight } from 'lucide-react';
import { api } from '../services/api';
import './LoginPage.css';

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
    <div className="lg-screen">
      <img src="/login-fondo.jpg" alt="" className="lg-bg" aria-hidden="true" />
      <div className="lg-shade" aria-hidden="true" />

      <section className="lg-card">
        <img src="/uide-logo-blanco.svg" alt="UIDE - Universidad Internacional del Ecuador" className="lg-logo" />
        <span className="lg-kicker">Posgrado UIDE</span>
        <h2>Iniciar sesión</h2>
        <p className="lg-lead">Gestión académica de los cursos preparatorios de maestría.</p>

        {error && <div className="lg-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Correo electrónico institucional</label>
            <div className="lg-field">
              <input
                type="email"
                className="form-input"
                placeholder="usuario@uide.edu.ec"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <Mail size={18} />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Contraseña</label>
            <div className="lg-field">
              <input
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <Lock size={18} />
            </div>
          </div>

          <button type="submit" className="btn btn-primary lg-submit" disabled={loading}>
            {loading ? 'Validando credenciales...' : 'Iniciar sesión'}
            <ArrowRight size={18} />
          </button>
        </form>

        <p className="lg-register">
          ¿Es postulante y aún no tiene cuenta?{' '}
          <button type="button" onClick={onShowRegister}>Crear cuenta</button>
        </p>
      </section>
    </div>
  );
}
