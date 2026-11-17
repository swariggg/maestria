import React, { useState, useEffect } from 'react';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { api } from '../services/api';
import Badge from './Badge';

const VACIO = { nombre: '', descripcion: '', es_obligatorio: true, formato_permitido: 'pdf', tamano_max_mb: 10 };

/** Requisitos documentales de una convocatoria: listar, crear, editar y eliminar. */
export default function RequirementsManager({ convocatoria, editable }) {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(null); // null = cerrado; { id?, ...campos }
  const [error, setError] = useState(null);

  const load = async () => {
    try {
      setItems(await api.getRequirements(convocatoria.id));
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => { load(); }, [convocatoria.id]);

  const setField = (campo) => (e) => {
    const valor = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm((prev) => ({ ...prev, [campo]: valor }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setError(null);
    const { id, ...datos } = form;
    datos.tamano_max_mb = parseInt(datos.tamano_max_mb, 10);
    datos.descripcion = datos.descripcion || null;
    try {
      if (id) await api.updateRequirement(id, datos);
      else await api.createRequirement({ convocatoria_id: convocatoria.id, ...datos });
      setForm(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (req) => {
    if (!window.confirm(`¿Eliminar el requisito "${req.nombre}"?`)) return;
    setError(null);
    try {
      await api.deleteRequirement(req.id);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div>
      <small style={{ display: 'block', marginBottom: '14px' }}>
        Si la convocatoria pide documentos obligatorios, el postulante se inscribe con la documentación pendiente
        y no aprueba hasta que coordinación los revise.
      </small>

      {error && <div className="notice-danger" style={{ marginBottom: '12px' }}>{error}</div>}

      {items.length === 0 && !form && (
        <div style={{ padding: '18px', textAlign: 'center', color: 'var(--text-sec)' }}>Esta convocatoria no pide documentos.</div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '14px' }}>
        {items.map((req) => (
          <div key={req.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', padding: '10px 14px', borderRadius: '12px', background: 'var(--surface-muted)', border: '1px solid var(--border-light)' }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                <strong style={{ fontSize: '0.9rem' }}>{req.nombre}</strong>
                <Badge type={req.es_obligatorio ? 'ALTO' : 'BAJO'} text={req.es_obligatorio ? 'Obligatorio' : 'Opcional'} />
              </div>
              <small style={{ color: 'var(--text-sec)' }}>
                {req.formato_permitido} · máx. {req.tamano_max_mb} MB{req.descripcion ? ` · ${req.descripcion}` : ''}
              </small>
            </div>
            {editable && (
              <div style={{ display: 'flex', gap: '6px' }}>
                <button className="btn btn-outline" style={{ padding: '6px 8px' }} title="Editar" onClick={() => setForm({ ...req })}>
                  <Pencil size={14} />
                </button>
                <button className="btn btn-outline" style={{ padding: '6px 8px' }} title="Eliminar" onClick={() => handleDelete(req)}>
                  <Trash2 size={14} />
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {editable && !form && (
        <button className="btn btn-secondary" onClick={() => { setError(null); setForm({ ...VACIO }); }}>
          <Plus size={15} />
          <span>Agregar requisito</span>
        </button>
      )}

      {form && (
        <form onSubmit={handleSave} style={{ padding: '14px', borderRadius: '14px', border: '1px solid var(--border-light)' }}>
          <div className="form-group">
            <label className="form-label">Nombre del documento</label>
            <input className="form-input" value={form.nombre} onChange={setField('nombre')} placeholder="Ej. Título de tercer nivel registrado en SENESCYT" minLength={3} maxLength={150} required />
          </div>
          <div className="form-group">
            <label className="form-label">Descripción</label>
            <input className="form-input" value={form.descripcion || ''} onChange={setField('descripcion')} placeholder="Indicaciones para el postulante" maxLength={500} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label className="form-label">Formatos (separados por coma)</label>
              <input className="form-input" value={form.formato_permitido} onChange={setField('formato_permitido')} placeholder="pdf,jpg" required />
            </div>
            <div className="form-group">
              <label className="form-label">Tamaño máximo (MB)</label>
              <input type="number" className="form-input" min="1" max="50" value={form.tamano_max_mb} onChange={setField('tamano_max_mb')} required />
            </div>
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem', marginBottom: '12px' }}>
            <input type="checkbox" checked={form.es_obligatorio} onChange={setField('es_obligatorio')} />
            Obligatorio para aprobar el proceso
          </label>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
            <button type="button" className="btn btn-outline" onClick={() => setForm(null)}>Cancelar</button>
            <button type="submit" className="btn btn-primary">{form.id ? 'Guardar cambios' : 'Agregar'}</button>
          </div>
        </form>
      )}
    </div>
  );
}
