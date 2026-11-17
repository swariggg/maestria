import React, { useState, useEffect } from 'react';
import { UserPlus, Pencil, KeyRound, Power, FolderTree } from 'lucide-react';
import { api } from '../services/api';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

const ROLES = { ADMIN: 'Administrador', COORDINADOR: 'Coordinador', TUTOR: 'Tutor', POSTULANTE: 'Postulante' };
const NUEVO = { rol: 'TUTOR', nombre_completo: '', email: '', cedula: '', telefono: '', password: '', especialidad: '', max_postulantes: 30, programa_ids: [] };

export default function UsersPage({ user }) {
  const [users, setUsers] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [filtro, setFiltro] = useState('');
  const [message, setMessage] = useState(null);
  const [modal, setModal] = useState(null); // { tipo: 'nuevo'|'editar'|'password'|'programas', usuario? }
  const [form, setForm] = useState({});
  const [modalError, setModalError] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      setUsers(await api.getUsers(filtro || undefined));
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  useEffect(() => { load(); }, [filtro]);
  useEffect(() => { api.getPrograms().then(setPrograms).catch(() => {}); }, []);

  const abrir = (tipo, usuario = null) => {
    setModalError(null);
    setModal({ tipo, usuario });
    if (tipo === 'nuevo') setForm({ ...NUEVO });
    if (tipo === 'editar') setForm({ nombre_completo: usuario.nombre_completo, telefono: usuario.telefono || '', especialidad: usuario.especialidad || '', max_postulantes: usuario.max_postulantes || 30 });
    if (tipo === 'password') setForm({ password: '', confirmar: '' });
    if (tipo === 'programas') setForm({ programa_ids: usuario.programas.map((p) => p.id) });
  };

  const setField = (campo) => (e) => setForm((prev) => ({ ...prev, [campo]: e.target.value }));
  const toggleProgram = (id) => setForm((prev) => ({
    ...prev,
    programa_ids: prev.programa_ids.includes(id) ? prev.programa_ids.filter((x) => x !== id) : [...prev.programa_ids, id],
  }));

  const guardar = async (e) => {
    e.preventDefault();
    setModalError(null);
    const u = modal.usuario;
    try {
      setSaving(true);
      let texto;
      if (modal.tipo === 'nuevo') {
        const datos = { ...form, max_postulantes: parseInt(form.max_postulantes, 10) || null, telefono: form.telefono || null };
        if (datos.rol !== 'TUTOR') { datos.especialidad = null; datos.max_postulantes = null; }
        await api.createUser(datos);
        texto = `Usuario ${form.email} creado. Al entrar por primera vez deberá cambiar la contraseña.`;
      } else if (modal.tipo === 'editar') {
        const datos = { nombre_completo: form.nombre_completo, telefono: form.telefono };
        if (u.rol === 'TUTOR') Object.assign(datos, { especialidad: form.especialidad, max_postulantes: parseInt(form.max_postulantes, 10) });
        await api.updateUser(u.id, datos);
        texto = `Datos de ${form.nombre_completo} actualizados.`;
      } else if (modal.tipo === 'password') {
        if (form.password !== form.confirmar) throw new Error('Las contraseñas no coinciden.');
        texto = `${(await api.resetUserPassword(u.id, form.password)).mensaje} Deberá cambiarla al iniciar sesión.`;
      } else {
        await api.setUserPrograms(u.id, form.programa_ids);
        texto = `Programas de ${u.nombre_completo} actualizados.`;
      }
      setModal(null);
      setMessage({ type: 'success', text: texto });
      load();
    } catch (err) {
      setModalError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const cambiarEstado = async (u) => {
    const nuevo = u.estado === 'ACTIVO' ? 'INACTIVO' : 'ACTIVO';
    if (nuevo === 'INACTIVO' && !window.confirm(`¿Desactivar la cuenta de ${u.nombre_completo}? No podrá iniciar sesión.`)) return;
    try {
      await api.setUserStatus(u.id, nuevo);
      setMessage({ type: 'success', text: `Cuenta de ${u.nombre_completo} ${nuevo === 'ACTIVO' ? 'activada' : 'desactivada'}.` });
      load();
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  const titulos = { nuevo: 'Nuevo usuario', editar: 'Editar usuario', password: 'Restablecer contraseña', programas: 'Programas asignados' };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: '16px', flexWrap: 'wrap', marginBottom: '24px' }}>
        <div>
          <h1>Gestión de Usuarios</h1>
          <p style={{ color: 'var(--text-sec)' }}>Coordinadores y tutores del sistema. Los postulantes se registran desde la pantalla de acceso.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <select className="form-select" value={filtro} onChange={(e) => setFiltro(e.target.value)} style={{ width: 'auto' }}>
            <option value="">Todos los roles</option>
            {Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <button className="btn btn-primary" onClick={() => abrir('nuevo')}>
            <UserPlus size={16} />
            <span>Nuevo usuario</span>
          </button>
        </div>
      </div>

      {message && (
        <div className={message.type === 'error' ? 'notice-danger' : 'notice-success'} style={{ marginBottom: '18px' }}>{message.text}</div>
      )}

      <div className="card" style={{ padding: 0 }}>
        <div className="table-responsive" style={{ border: 'none' }}>
          <table className="table">
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Rol</th>
                <th>Detalle</th>
                <th>Estado</th>
                <th style={{ textAlign: 'right' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>
                    <strong>{u.nombre_completo}</strong>
                    <div><small style={{ color: 'var(--text-sec)' }}>{u.email} · CI {u.cedula}</small></div>
                  </td>
                  <td>{ROLES[u.rol] || u.rol}</td>
                  <td>
                    <small>
                      {u.rol === 'TUTOR' && `${u.especialidad} · cupo ${u.max_postulantes} · ${u.programas.length ? u.programas.map((p) => p.codigo).join(', ') : 'sin programas'}`}
                      {u.rol === 'COORDINADOR' && (u.programas.length ? u.programas.map((p) => p.codigo).join(', ') : 'Sin programas')}
                      {u.telefono && u.rol !== 'TUTOR' && u.rol !== 'COORDINADOR' && u.telefono}
                    </small>
                  </td>
                  <td><Badge type={u.estado} text={u.estado} /></td>
                  <td>
                    <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                      <button className="btn btn-outline" style={{ padding: '6px 8px' }} title="Editar datos" onClick={() => abrir('editar', u)}>
                        <Pencil size={14} />
                      </button>
                      {['COORDINADOR', 'TUTOR'].includes(u.rol) && (
                        <button className="btn btn-outline" style={{ padding: '6px 8px' }} title="Programas asignados" onClick={() => abrir('programas', u)}>
                          <FolderTree size={14} />
                        </button>
                      )}
                      <button className="btn btn-outline" style={{ padding: '6px 8px' }} title="Restablecer contraseña" onClick={() => abrir('password', u)}>
                        <KeyRound size={14} />
                      </button>
                      {u.id !== user?.id && (
                        <button className="btn btn-outline" style={{ padding: '6px 8px' }} title={u.estado === 'ACTIVO' ? 'Desactivar' : 'Activar'} onClick={() => cambiarEstado(u)}>
                          <Power size={14} color={u.estado === 'ACTIVO' ? 'var(--color-danger, #B91C1C)' : 'var(--color-success, #047857)'} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-sec)', padding: '24px' }}>No hay usuarios para este filtro.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <Modal isOpen={!!modal} onClose={() => setModal(null)} title={modal ? titulos[modal.tipo] : ''}>
        {modal && (
          <form onSubmit={guardar}>
            {modalError && <div className="notice-danger" style={{ marginBottom: '12px' }}>{modalError}</div>}

            {modal.tipo === 'nuevo' && (
              <>
                <div className="form-group">
                  <label className="form-label">Rol</label>
                  <select className="form-select" value={form.rol} onChange={setField('rol')}>
                    <option value="TUTOR">Tutor</option>
                    <option value="COORDINADOR">Coordinador</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Nombre completo</label>
                  <input className="form-input" value={form.nombre_completo} onChange={setField('nombre_completo')} minLength={3} required />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label">Correo</label>
                    <input type="email" className="form-input" value={form.email} onChange={setField('email')} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Cédula</label>
                    <input className="form-input" value={form.cedula} onChange={setField('cedula')} minLength={10} maxLength={20} required />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label">Teléfono</label>
                    <input className="form-input" value={form.telefono} onChange={setField('telefono')} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Contraseña inicial</label>
                    <input type="password" className="form-input" value={form.password} onChange={setField('password')} minLength={8} required />
                  </div>
                </div>
              </>
            )}

            {modal.tipo === 'editar' && (
              <>
                <div className="form-group">
                  <label className="form-label">Nombre completo</label>
                  <input className="form-input" value={form.nombre_completo} onChange={setField('nombre_completo')} minLength={3} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Teléfono</label>
                  <input className="form-input" value={form.telefono} onChange={setField('telefono')} />
                </div>
              </>
            )}

            {((modal.tipo === 'nuevo' && form.rol === 'TUTOR') || (modal.tipo === 'editar' && modal.usuario.rol === 'TUTOR')) && (
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">Especialidad</label>
                  <input className="form-input" value={form.especialidad} onChange={setField('especialidad')} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Cupo de postulantes</label>
                  <input type="number" min="1" max="500" className="form-input" value={form.max_postulantes} onChange={setField('max_postulantes')} required />
                </div>
              </div>
            )}

            {modal.tipo === 'password' && (
              <>
                <p style={{ marginBottom: '12px', color: 'var(--text-sec)' }}>Contraseña temporal para <strong>{modal.usuario.nombre_completo}</strong>. Entréguesela por un canal seguro; deberá cambiarla al entrar. Use al menos 8 caracteres con letras y números.</p>
                <div className="form-group">
                  <label className="form-label">Nueva contraseña</label>
                  <input type="password" className="form-input" value={form.password} onChange={setField('password')} minLength={8} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Confirmar contraseña</label>
                  <input type="password" className="form-input" value={form.confirmar} onChange={setField('confirmar')} minLength={8} required />
                </div>
              </>
            )}

            {(modal.tipo === 'programas' || (modal.tipo === 'nuevo' && ['COORDINADOR', 'TUTOR'].includes(form.rol))) && (
              <div className="form-group">
                <label className="form-label">
                  {(modal.tipo === 'nuevo' ? form.rol : modal.usuario.rol) === 'TUTOR' ? 'Programas donde puede acompañar postulantes' : 'Programas que coordina'}
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '220px', overflowY: 'auto' }}>
                  {programs.map((p) => (
                    <label key={p.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem' }}>
                      <input type="checkbox" checked={form.programa_ids.includes(p.id)} onChange={() => toggleProgram(p.id)} />
                      {p.codigo} - {p.nombre}
                    </label>
                  ))}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
              <button type="button" className="btn btn-outline" onClick={() => setModal(null)}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Guardando...' : 'Guardar'}</button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
