import React, { useState, useEffect } from 'react';
import { UserRound, FolderOpen, Save, LogOut, Award, Link2 } from 'lucide-react';
import { api } from '../services/api';
import Badge from '../components/Badge';
import DocumentsPanel from '../components/DocumentsPanel';
import ProfilePhoto from '../components/ProfilePhoto';
import TutorProfile from '../components/TutorProfile';

const CERRADAS = ['APROBADO', 'NO_APROBADO', 'RETIRADO'];

const CAMPOS = [
  { campo: 'nombre_completo', label: 'Nombres y apellidos', placeholder: 'María José Pérez López', ancho: true },
  { campo: 'cedula', label: 'Cédula', placeholder: '1712345678' },
  { campo: 'fecha_nacimiento', label: 'Fecha de nacimiento', tipo: 'date' },
  { campo: 'telefono', label: 'Teléfono celular', placeholder: '0991234567' },
  { campo: 'direccion', label: 'Dirección', placeholder: 'Av. Simón Bolívar y Calle 1' },
  { campo: 'ciudad', label: 'Ciudad', placeholder: 'Quito' },
  { campo: 'pais', label: 'País', placeholder: 'Ecuador' },
  { campo: 'titulo_tercer_nivel', label: 'Título de tercer nivel', placeholder: 'Ingeniero(a) en Sistemas' },
  { campo: 'universidad_origen', label: 'Universidad de origen', placeholder: 'Universidad Central del Ecuador' },
  { campo: 'contacto_emergencia', label: 'Contacto de emergencia', placeholder: 'Nombre y parentesco' },
  { campo: 'telefono_emergencia', label: 'Teléfono de emergencia', placeholder: '0987654321' },
];

export default function ProfilePage({ user }) {
  if (user?.rol?.codigo === 'TUTOR') return <TutorProfile user={user} />;
  return <ApplicantProfile user={user} />;
}

function ApplicantProfile({ user }) {
  const [form, setForm] = useState(null);
  const [inscripciones, setInscripciones] = useState([]);
  const [inscripcionId, setInscripcionId] = useState(null);
  const [motivoRetiro, setMotivoRetiro] = useState('');
  const [mostrarRetiro, setMostrarRetiro] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [perfil, mias] = await Promise.all([api.getMyProfile(), api.getMyEnrollments()]);
        setForm(perfil);
        setInscripciones(mias);
        setInscripcionId((mias.find((i) => !CERRADAS.includes(i.estado_proceso)) || mias[0] || {}).id || null);
      } catch (err) {
        setMessage({ type: 'error', text: err.message });
      }
    })();
  }, []);

  const setField = (campo) => (e) => {
    const valor = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm((prev) => ({ ...prev, [campo]: valor }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const payload = {};
      [...CAMPOS.map((c) => c.campo), 'registrado_senescyt', 'enlaces'].forEach((c) => { payload[c] = form[c] === '' ? null : form[c]; });
      const actualizado = await api.updateMyProfile(payload);
      setForm(actualizado);
      if (user && (actualizado.nombre_completo !== user.nombre_completo || actualizado.cedula !== user.cedula)) {
        try {
          localStorage.setItem('user', JSON.stringify({ ...user, nombre_completo: actualizado.nombre_completo, cedula: actualizado.cedula }));
        } catch { /* sin almacenamiento local */ }
      }
      setMessage({ type: 'success', text: actualizado.perfil_completo ? 'Perfil guardado. Sus datos están completos.' : 'Perfil guardado. Aún faltan algunos datos.' });
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
    }
  };

  const inscripcion = inscripciones.find((i) => i.id === inscripcionId) || null;

  const recargarInscripciones = async () => setInscripciones(await api.getMyEnrollments());

  const handleRetiro = async () => {
    setMessage(null);
    try {
      const res = await api.requestWithdrawal(inscripcion.id, motivoRetiro);
      setMessage({ type: 'success', text: res.mensaje });
      setMostrarRetiro(false);
      setMotivoRetiro('');
      await recargarInscripciones();
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  const descargarCertificado = async () => {
    try {
      const blob = await api.downloadCertificate(inscripcion.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `certificado_${form.cedula}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  if (!form) {
    return <div style={{ textAlign: 'center', padding: '60px' }}>{message ? message.text : 'Cargando perfil...'}</div>;
  }

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1>Mi Perfil</h1>
        <p style={{ color: 'var(--text-sec)' }}>
          Complete sus datos personales y cargue los documentos que pide su convocatoria.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px', alignItems: 'start' }}>
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', marginBottom: '16px', flexWrap: 'wrap' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <UserRound size={18} color="var(--color-navy)" />
              <span>Datos personales</span>
            </h3>
            <Badge type={form.perfil_completo ? 'APROBADO' : 'MEDIO'} text={form.perfil_completo ? 'Completo' : 'Incompleto'} />
          </div>

          <div style={{ padding: '14px', borderRadius: '12px', background: 'var(--surface-muted)', marginBottom: '16px', fontSize: '0.875rem', display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
            <ProfilePhoto usuarioId={user?.id} nombre={form.nombre_completo} tieneFoto={form.tiene_foto} editable
              onChange={(tiene) => setForm((prev) => ({ ...prev, tiene_foto: tiene }))} />
            <div>
              <strong>{form.nombre_completo}</strong>
              <div style={{ color: 'var(--text-sec)' }}>CI: {form.cedula} · {form.email}</div>
              <small style={{ color: 'var(--text-sec)' }}>Su foto solo se ve aquí, en su perfil.</small>
            </div>
          </div>

          {message && (
            <div className={message.type === 'error' ? 'notice-danger' : 'notice-success'} style={{ marginBottom: '14px' }}>
              {message.text}
            </div>
          )}

          <form onSubmit={handleSave}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0 12px' }}>
              {CAMPOS.map(({ campo, label, placeholder, tipo, ancho }) => (
                <div className="form-group" key={campo} style={ancho ? { gridColumn: '1 / -1' } : undefined}>
                  <label className="form-label">{label}</label>
                  <input className="form-input" type={tipo || 'text'} value={form[campo] || ''} placeholder={placeholder} onChange={setField(campo)} />
                </div>
              ))}
            </div>
            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Link2 size={14} /> Enlaces (LinkedIn, portafolio...), uno por línea
              </label>
              <textarea className="form-input" rows={2} value={form.enlaces || ''} placeholder="https://www.linkedin.com/in/su-perfil" onChange={setField('enlaces')} />
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem', margin: '4px 0 16px' }}>
              <input type="checkbox" checked={!!form.registrado_senescyt} onChange={setField('registrado_senescyt')} />
              Mi título está registrado en la SENESCYT
            </label>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                <Save size={16} />
                <span>{saving ? 'Guardando...' : 'Guardar perfil'}</span>
              </button>
            </div>
          </form>
        </div>

        <div className="card">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <FolderOpen size={18} color="var(--color-navy)" />
            <span>Mis documentos</span>
          </h3>
          {inscripciones.length > 1 && (
            <div className="form-group">
              <label className="form-label">Inscripción</label>
              <select className="form-select" value={inscripcionId || ''} onChange={(e) => setInscripcionId(Number(e.target.value))}>
                {inscripciones.map((i) => (
                  <option key={i.id} value={i.id}>{i.programa_nombre} · {i.convocatoria_nombre} ({i.estado_proceso})</option>
                ))}
              </select>
            </div>
          )}
          {inscripcion ? (
            <>
              <DocumentsPanel key={inscripcion.id} inscripcionId={inscripcion.id} modo="postulante" />

              <div style={{ borderTop: '1px solid var(--border-light)', marginTop: '18px', paddingTop: '14px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                {inscripcion.estado_proceso === 'APROBADO' && (
                  <button type="button" className="btn btn-primary" onClick={descargarCertificado}>
                    <Award size={16} /> <span>Descargar certificado</span>
                  </button>
                )}
                {!CERRADAS.includes(inscripcion.estado_proceso) && (
                  inscripcion.retiro_solicitado ? (
                    <Badge type="MEDIO" text="Retiro solicitado: esperando respuesta de coordinación" />
                  ) : (
                    <button type="button" className="btn btn-outline" onClick={() => setMostrarRetiro(!mostrarRetiro)}>
                      <LogOut size={16} /> <span>Solicitar retiro</span>
                    </button>
                  )
                )}
              </div>
              {mostrarRetiro && (
                <div style={{ marginTop: '12px' }}>
                  <label className="form-label">¿Por qué desea retirarse? (mínimo 10 caracteres)</label>
                  <textarea className="form-input" rows={3} value={motivoRetiro} onChange={(e) => setMotivoRetiro(e.target.value)} />
                  <small style={{ color: 'var(--text-sec)', display: 'block', margin: '6px 0 10px' }}>
                    Coordinación revisará su solicitud y le responderá con un aviso en la app. Hasta entonces su inscripción sigue vigente.
                  </small>
                  <button type="button" className="btn btn-primary" disabled={motivoRetiro.trim().length < 10} onClick={handleRetiro}>
                    Enviar solicitud
                  </button>
                </div>
              )}
            </>
          ) : (
            <p style={{ color: 'var(--text-sec)' }}>
              Cuando se inscriba en una convocatoria, aquí aparecerán los documentos que debe entregar.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
