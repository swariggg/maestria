import React, { useState, useEffect } from 'react';
import { UserRound, Save, Eye } from 'lucide-react';
import { api } from '../services/api';
import ProfilePhoto from './ProfilePhoto';
import { TutorContact } from './TutorCard';

const CAMPOS = [
  { campo: 'especialidad', label: 'Especialidad *', placeholder: 'Inteligencia Artificial' },
  { campo: 'telefono', label: 'Teléfono (opcional)', placeholder: '0991234567' },
  { campo: 'correo_outlook', label: 'Correo de Outlook', placeholder: 'nombre.apellido@uide.edu.ec' },
  { campo: 'usuario_teams', label: 'Cuenta de Teams', placeholder: 'nombre.apellido@uide.edu.ec' },
  { campo: 'horario_atencion', label: 'Horario de atención', placeholder: 'Lunes y miércoles de 18:00 a 20:00', ancho: true },
];

/** Perfil del tutor: foto y datos de contacto que sus postulantes ven en la portada de cada curso. */
export default function TutorProfile({ user }) {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    api.getTutorProfile().then(setForm).catch((err) => setMessage({ type: 'error', text: err.message }));
  }, []);

  const setField = (campo) => (e) => setForm((prev) => ({ ...prev, [campo]: e.target.value }));

  const guardar = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const payload = {};
      [...CAMPOS.map((c) => c.campo), 'presentacion'].forEach((c) => { payload[c] = form[c] === '' ? null : form[c]; });
      setForm(await api.updateTutorProfile(payload));
      setMessage({ type: 'success', text: 'Perfil guardado. Sus postulantes ya ven estos datos en sus cursos.' });
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
    }
  };

  if (!form) return <div style={{ textAlign: 'center', padding: '60px' }}>{message ? message.text : 'Cargando perfil...'}</div>;

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1>Mi Perfil</h1>
        <p style={{ color: 'var(--text-sec)' }}>
          Estos datos aparecen en la portada de sus cursos para que los postulantes sepan cómo contactarle.
          El correo y Teams son solo enlaces: la app no se conecta a esas cuentas.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px', alignItems: 'start' }}>
        <div className="card">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <UserRound size={18} color="var(--color-navy)" /> <span>Datos de contacto</span>
          </h3>
          <div style={{ padding: '14px', borderRadius: '12px', background: 'var(--surface-muted)', marginBottom: '16px' }}>
            <ProfilePhoto usuarioId={form.usuario_id || user?.id} nombre={form.nombre_completo} tieneFoto={form.tiene_foto} editable
              onChange={(tiene) => setForm((prev) => ({ ...prev, tiene_foto: tiene }))} />
          </div>
          {message && (
            <div className={message.type === 'error' ? 'notice-danger' : 'notice-success'} style={{ marginBottom: '14px' }}>{message.text}</div>
          )}
          <form onSubmit={guardar}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0 12px' }}>
              {CAMPOS.map(({ campo, label, placeholder, ancho }) => (
                <div className="form-group" key={campo} style={ancho ? { gridColumn: '1 / -1' } : undefined}>
                  <label className="form-label">{label}</label>
                  <input className="form-input" value={form[campo] || ''} placeholder={placeholder} onChange={setField(campo)} />
                </div>
              ))}
            </div>
            <div className="form-group">
              <label className="form-label">Presentación breve</label>
              <textarea className="form-input" rows={4} maxLength={1000} value={form.presentacion || ''}
                placeholder="Cuénteles a sus postulantes quién es y cómo trabajará con ellos." onChange={setField('presentacion')} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button type="submit" className="btn btn-primary" disabled={saving || !(form.especialidad || '').trim()}>
                <Save size={16} /> <span>{saving ? 'Guardando...' : 'Guardar perfil'}</span>
              </button>
            </div>
          </form>
        </div>

        <div className="card" style={{ borderLeft: '4px solid var(--color-uide)' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Eye size={18} color="var(--color-navy)" /> <span>Así le ven sus postulantes</span>
          </h3>
          <TutorContact tutor={form} />
        </div>
      </div>
    </div>
  );
}
