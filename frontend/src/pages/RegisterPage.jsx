import React, { useState } from 'react';
import { GraduationCap, ArrowLeft, UserPlus } from 'lucide-react';
import { api } from '../services/api';

const initialForm = {
  nombre_completo: '',
  cedula: '',
  email: '',
  telefono: '',
  ciudad: '',
  titulo_tercer_nivel: '',
  universidad_origen: '',
  password: '',
  confirmar: ''
};

export default function RegisterPage({ onRegistered, onBack }) {
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (form.password !== form.confirmar) {
      setError('Las contraseñas no coinciden.');
      return;
    }

    setLoading(true);
    try {
      const { confirmar, ...payload } = form;
      Object.keys(payload).forEach((k) => {
        if (payload[k] === '') payload[k] = null;
      });
      await api.register(payload);

      // Iniciar sesión automáticamente con la cuenta recién creada
      const data = await api.login({ email: form.email, password: form.password });
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      onRegistered(data.user);
    } catch (err) {
      setError(err.message || 'No se pudo completar el registro.');
    } finally {
      setLoading(false);
    }
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
      <div className="card" style={{ maxWidth: '560px', width: '100%', padding: '36px' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{
            display: 'inline-flex',
            background: 'var(--color-primary)',
            padding: '14px',
            borderRadius: '20px',
            marginBottom: '16px'
          }}>
            <GraduationCap size={36} color="#701A48" />
          </div>
          <h1>Crear Cuenta de Postulante</h1>
          <p style={{ color: 'var(--text-sec)', marginTop: '4px' }}>
            Regístrese para inscribirse en un curso preparatorio de maestría.
          </p>
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
            <label className="form-label">Nombre Completo *</label>
            <input name="nombre_completo" className="form-input" value={form.nombre_completo} onChange={handleChange} minLength={3} required />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0 16px' }}>
            <div className="form-group">
              <label className="form-label">Cédula / Pasaporte *</label>
              <input name="cedula" className="form-input" value={form.cedula} onChange={handleChange} minLength={10} maxLength={20} required />
            </div>
            <div className="form-group">
              <label className="form-label">Teléfono</label>
              <input name="telefono" className="form-input" value={form.telefono} onChange={handleChange} />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Correo Electrónico *</label>
            <input type="email" name="email" className="form-input" value={form.email} onChange={handleChange} required />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0 16px' }}>
            <div className="form-group">
              <label className="form-label">Título de Tercer Nivel</label>
              <input name="titulo_tercer_nivel" className="form-input" value={form.titulo_tercer_nivel} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label className="form-label">Universidad de Origen</label>
              <input name="universidad_origen" className="form-input" value={form.universidad_origen} onChange={handleChange} />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Ciudad</label>
            <input name="ciudad" className="form-input" value={form.ciudad} onChange={handleChange} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0 16px' }}>
            <div className="form-group">
              <label className="form-label">Contraseña * (mín. 8)</label>
              <input type="password" name="password" className="form-input" value={form.password} onChange={handleChange} minLength={8} required />
            </div>
            <div className="form-group">
              <label className="form-label">Confirmar Contraseña *</label>
              <input type="password" name="confirmar" className="form-input" value={form.confirmar} onChange={handleChange} minLength={8} required />
            </div>
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '8px', padding: '12px' }} disabled={loading}>
            <UserPlus size={18} />
            {loading ? 'Creando cuenta...' : 'Crear Cuenta'}
          </button>
        </form>

        <button type="button" className="btn btn-outline" style={{ width: '100%', marginTop: '12px' }} onClick={onBack}>
          <ArrowLeft size={16} />
          Ya tengo cuenta, iniciar sesión
        </button>
      </div>
    </div>
  );
}
