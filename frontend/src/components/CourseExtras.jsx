import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Download, Link as LinkIcon, Video, FileText, Save } from 'lucide-react';
import { api } from '../services/api';
import { saveBlob } from '../utils/download';

/**
 * Rúbrica de una actividad: criterios con su puntaje máximo. La suma debe ser igual a la
 * ponderación de la actividad. No se puede cambiar cuando ya hay entregas calificadas.
 */
export function RubricEditor({ actividad, onClose }) {
  const [criterios, setCriterios] = useState(null);
  const [error, setError] = useState(null);
  const [ok, setOk] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getCriteria(actividad.id)
      .then((r) => setCriterios(r.criterios.map((c) => ({ criterio: c.criterio, puntaje_maximo: c.puntaje_maximo }))))
      .catch((err) => setError(err.message));
  }, [actividad.id]);

  if (!criterios) return <div style={{ padding: '20px', textAlign: 'center' }}>{error || 'Cargando rúbrica...'}</div>;

  const suma = criterios.reduce((t, c) => t + (parseFloat(c.puntaje_maximo) || 0), 0);
  const ponderacion = parseFloat(actividad.ponderacion);
  const cambiar = (i, campo, valor) => setCriterios(criterios.map((c, j) => (j === i ? { ...c, [campo]: valor } : c)));

  const guardar = async (e) => {
    e.preventDefault();
    setError(null);
    setOk(null);
    setSaving(true);
    try {
      await api.setCriteria(actividad.id, criterios.map((c) => ({ criterio: c.criterio, puntaje_maximo: parseFloat(c.puntaje_maximo) })));
      setOk(criterios.length ? 'Rúbrica guardada. La nota será la suma de los criterios.' : 'Rúbrica eliminada. La nota se pone directamente.');
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={guardar}>
      <p style={{ fontSize: '0.875rem', color: 'var(--text-sec)', marginBottom: '12px' }}>
        Con rúbrica, quien califica pone un puntaje por criterio y la nota es la suma. Los puntajes máximos deben
        sumar la ponderación de la actividad ({ponderacion} puntos). Sin criterios, la nota se pone directamente.
      </p>
      {error && <div className="notice-danger" style={{ marginBottom: '12px' }}>{error}</div>}
      {ok && <div className="notice-success" style={{ marginBottom: '12px' }}>{ok}</div>}

      {criterios.map((c, i) => (
        <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 120px auto', gap: '8px', marginBottom: '8px' }}>
          <input className="form-input" placeholder="Criterio (ej.: claridad del análisis)" value={c.criterio}
            onChange={(e) => cambiar(i, 'criterio', e.target.value)} minLength={3} required />
          <input type="number" step="0.01" min="0.01" className="form-input" placeholder="Puntos" value={c.puntaje_maximo}
            onChange={(e) => cambiar(i, 'puntaje_maximo', e.target.value)} required />
          <button type="button" className="btn btn-outline" style={{ padding: '6px 10px' }} title="Quitar"
            onClick={() => setCriterios(criterios.filter((_, j) => j !== i))}>
            <Trash2 size={14} />
          </button>
        </div>
      ))}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginTop: '8px' }}>
        <button type="button" className="btn btn-outline" onClick={() => setCriterios([...criterios, { criterio: '', puntaje_maximo: '' }])}>
          <Plus size={14} /> <span>Agregar criterio</span>
        </button>
        <small style={{ fontWeight: 600, color: criterios.length && Math.abs(suma - ponderacion) > 0.001 ? 'var(--status-danger-text)' : 'var(--text-sec)' }}>
          Suma: {suma.toFixed(2)} / {ponderacion}
        </small>
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '18px' }}>
        <button type="button" className="btn btn-outline" onClick={onClose}>Cerrar</button>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          <Save size={14} /> <span>{saving ? 'Guardando...' : 'Guardar rúbrica'}</span>
        </button>
      </div>
    </form>
  );
}

const TIPO_ICONO = { ARCHIVO: FileText, ENLACE: LinkIcon, SESION: Video };
const TIPO_TEXTO = { ARCHIVO: 'Archivo', ENLACE: 'Enlace', SESION: 'Sesión en vivo' };
const NUEVO = { tipo: 'ARCHIVO', titulo: '', descripcion: '', url: '', fecha_sesion: '' };

/** Materiales del curso: lecturas, enlaces y sesiones sincrónicas (Teams o Zoom). */
export function MaterialsPanel({ curso }) {
  const [data, setData] = useState(null);
  const [form, setForm] = useState(NUEVO);
  const [file, setFile] = useState(null);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [message, setMessage] = useState(null);
  const [saving, setSaving] = useState(false);
  const [fallo, setFallo] = useState(false);

  const load = async () => {
    try {
      setData(await api.getMaterials(curso.id));
      setFallo(false);
    } catch (err) {
      setFallo(true);
      setMessage({ type: 'error', text: err.message });
    }
  };

  useEffect(() => {
    setData(null);
    setFallo(false);
    setMostrarForm(false);
    load();
  }, [curso.id]);

  const set = (campo) => (e) => setForm({ ...form, [campo]: e.target.value });

  const guardar = async (e) => {
    e.preventDefault();
    setMessage(null);
    setSaving(true);
    try {
      const fd = new FormData();
      fd.append('curso_id', curso.id);
      fd.append('tipo', form.tipo);
      fd.append('titulo', form.titulo);
      if (form.descripcion) fd.append('descripcion', form.descripcion);
      if (form.tipo !== 'ARCHIVO') fd.append('url', form.url);
      if (form.tipo === 'SESION') fd.append('fecha_sesion', `${form.fecha_sesion}:00`);
      if (form.tipo === 'ARCHIVO' && file) fd.append('file', file);
      await api.createMaterial(fd);
      setForm(NUEVO);
      setFile(null);
      setMostrarForm(false);
      setMessage({ type: 'success', text: 'Material publicado. Los postulantes del curso ya lo ven.' });
      await load();
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
    }
  };

  const eliminar = async (m) => {
    if (!window.confirm(`¿Eliminar "${m.titulo}"?`)) return;
    try {
      await api.deleteMaterial(m.id);
      await load();
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  const descargar = async (m) => {
    try {
      saveBlob(await api.downloadMaterial(m.id), m.nombre_original);
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  return (
    <div className="card" style={{ marginTop: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '14px' }}>
        <h3>Materiales y sesiones de {curso.nombre}</h3>
        {data?.puede_gestionar && (
          <button className="btn btn-primary" onClick={() => setMostrarForm(!mostrarForm)}>
            <Plus size={16} /> <span>Agregar material</span>
          </button>
        )}
      </div>

      {message && (
        <div className={message.type === 'error' ? 'notice-danger' : 'notice-success'} style={{ marginBottom: '12px' }}>{message.text}</div>
      )}

      {mostrarForm && (
        <form onSubmit={guardar} style={{ padding: '14px', borderRadius: '14px', background: 'var(--surface-muted)', marginBottom: '16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0 12px' }}>
            <div className="form-group">
              <label className="form-label">Tipo</label>
              <select className="form-select" value={form.tipo} onChange={set('tipo')}>
                {Object.entries(TIPO_TEXTO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Título</label>
              <input className="form-input" value={form.titulo} onChange={set('titulo')} minLength={3} required />
            </div>
            {form.tipo === 'ARCHIVO' && (
              <div className="form-group">
                <label className="form-label">Archivo (máx. 50 MB)</label>
                <input type="file" className="form-input" onChange={(e) => setFile(e.target.files[0] || null)} required />
              </div>
            )}
            {form.tipo !== 'ARCHIVO' && (
              <div className="form-group">
                <label className="form-label">{form.tipo === 'SESION' ? 'Enlace de la reunión (Teams o Zoom)' : 'Enlace'}</label>
                <input type="url" className="form-input" placeholder="https://..." value={form.url} onChange={set('url')} required />
              </div>
            )}
            {form.tipo === 'SESION' && (
              <div className="form-group">
                <label className="form-label">Fecha y hora</label>
                <input type="datetime-local" className="form-input" value={form.fecha_sesion} onChange={set('fecha_sesion')} required />
              </div>
            )}
          </div>
          <div className="form-group">
            <label className="form-label">Descripción (opcional)</label>
            <input className="form-input" value={form.descripcion} onChange={set('descripcion')} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
            <button type="button" className="btn btn-outline" onClick={() => setMostrarForm(false)}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Publicando...' : 'Publicar'}</button>
          </div>
        </form>
      )}

      {!data ? (
        fallo ? null : <p>Cargando materiales...</p>
      ) : data.materiales.length === 0 ? (
        <small>Este curso todavía no tiene materiales.</small>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {data.materiales.map((m) => {
            const Icono = TIPO_ICONO[m.tipo] || FileText;
            return (
              <div key={m.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap', padding: '12px 14px', borderRadius: '12px', border: '1px solid var(--border-light)' }}>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start', minWidth: 0 }}>
                  <Icono size={18} color="var(--color-navy)" style={{ flexShrink: 0, marginTop: '2px' }} />
                  <div style={{ minWidth: 0 }}>
                    <strong style={{ fontSize: '0.9rem' }}>{m.titulo}</strong>
                    <small style={{ display: 'block', color: 'var(--text-sec)' }}>
                      {TIPO_TEXTO[m.tipo]}
                      {m.fecha_sesion && ` · ${new Date(m.fecha_sesion).toLocaleString('es-EC', { dateStyle: 'medium', timeStyle: 'short' })}`}
                      {m.subido_por && ` · ${m.subido_por}`}
                    </small>
                    {m.descripcion && <small style={{ display: 'block' }}>{m.descripcion}</small>}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  {m.tiene_archivo ? (
                    <button className="btn btn-outline" style={{ padding: '6px 10px' }} onClick={() => descargar(m)}>
                      <Download size={14} /> <span>Descargar</span>
                    </button>
                  ) : m.url && (
                    <a className="btn btn-outline" style={{ padding: '6px 10px' }} href={m.url} target="_blank" rel="noopener noreferrer">
                      <LinkIcon size={14} /> <span>{m.tipo === 'SESION' ? 'Entrar' : 'Abrir'}</span>
                    </a>
                  )}
                  {data.puede_gestionar && (
                    <button className="btn btn-outline" style={{ padding: '6px 8px' }} title="Eliminar" onClick={() => eliminar(m)}>
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
