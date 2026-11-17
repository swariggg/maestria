import React, { useState } from 'react';
import { KeyRound, LogOut } from 'lucide-react';
import { api } from '../services/api';

/**
 * Primera entrada de una cuenta creada o restablecida por el administrador:
 * el usuario debe cambiar la contraseña temporal antes de usar la aplicación.
 */
export default function ChangePasswordPage({ user, onChanged, onLogout }) {
  const [actual, setActual] = useState('');
  const [nueva, setNueva] = useState('');
  const [repetir, setRepetir] = useState('');
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (nueva !== repetir) {
      setError('Las contraseñas nuevas no coinciden.');
      return;
    }
    if (nueva === actual) {
      setError('La contraseña nueva debe ser distinta de la temporal.');
      return;
    }
    setSaving(true);
    try {
      await api.changeInitialPassword({ password_actual: actual, password_nueva: nueva });
      onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="auth-screen">
      <div className="card" style={{ maxWidth: '460px', width: '100%', padding: '36px' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <img src="/uide-logo.svg" alt="UIDE" style={{ height: '56px', marginBottom: '16px' }} />
          <h2 style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
            <KeyRound size={22} /> Cambie su contraseña
          </h2>
          <p style={{ color: 'var(--text-sec)', marginTop: '6px' }}>
            Hola, {user.nombre_completo}. Su cuenta tiene una contraseña temporal asignada por el administrador.
            Antes de continuar, elija una propia.
          </p>
        </div>

        {error && (
          <div style={{
            background: 'var(--status-danger-bg)', color: 'var(--status-danger-text)', padding: '12px 16px',
            borderRadius: '12px', marginBottom: '16px', fontSize: '0.875rem', border: '1px solid var(--status-danger-border)'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Contraseña temporal</label>
            <input type="password" className="form-input" value={actual} onChange={(e) => setActual(e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Contraseña nueva</label>
            <input type="password" className="form-input" value={nueva} onChange={(e) => setNueva(e.target.value)} minLength={8} required />
            <small style={{ color: 'var(--text-sec)' }}>Al menos 8 caracteres, con letras y números.</small>
          </div>
          <div className="form-group">
            <label className="form-label">Repita la contraseña nueva</label>
            <input type="password" className="form-input" value={repetir} onChange={(e) => setRepetir(e.target.value)} minLength={8} required />
          </div>
          <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '12px' }} disabled={saving}>
            {saving ? 'Guardando...' : 'Guardar y continuar'}
          </button>
        </form>
        <button type="button" className="btn btn-outline" style={{ width: '100%', marginTop: '10px' }} onClick={onLogout}>
          <LogOut size={16} /> Salir
        </button>
      </div>
    </div>
  );
}
