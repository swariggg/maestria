import React, { useState, useEffect } from 'react';
import { SlidersHorizontal, Save } from 'lucide-react';
import { api } from '../services/api';
import Badge from '../components/Badge';

const ETIQUETA = {
  DIAS_INACTIVIDAD_RIESGO: 'Días de inactividad para riesgo alto',
  INTENTOS_SIN_RESPUESTA_ALERTA: 'Contactos sin respuesta para riesgo alto',
  DIAS_PROXIMA_A_VENCER: 'Días para "próxima a vencer"',
  MARGEN_BAJO_AVANCE: 'Margen de bajo avance (puntos)',
  DIAS_RECORDATORIO: 'Días de recordatorio antes del vencimiento',
};

export default function ConfigPage() {
  const [params, setParams] = useState([]);
  const [valores, setValores] = useState({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  const aplicar = (lista) => {
    setParams(lista);
    setValores(Object.fromEntries(lista.map((p) => [p.clave, p.valor])));
  };

  useEffect(() => {
    api.getParameters().then(aplicar).catch((err) => setMessage({ type: 'error', text: err.message }));
  }, []);

  const cambiados = params.filter((p) => String(valores[p.clave]) !== String(p.valor));

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const res = await api.updateParameters(Object.fromEntries(cambiados.map((p) => [p.clave, String(valores[p.clave])])));
      aplicar(res.parametros);
      setMessage({ type: 'success', text: `${res.mensaje} Se aplican en la próxima evaluación de riesgo y de recordatorios.` });
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
    }
  };

  const categorias = [...new Set(params.map((p) => p.categoria))];

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1>Configuración del Proceso</h1>
        <p style={{ color: 'var(--text-sec)' }}>
          Plazos y umbrales que usan el motor de riesgo y los recordatorios. Cada cambio queda en la auditoría.
        </p>
      </div>

      {message && (
        <div className={message.type === 'error' ? 'notice-danger' : 'notice-success'} style={{ marginBottom: '18px' }}>
          {message.text}
        </div>
      )}

      <form onSubmit={handleSave}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px', alignItems: 'start' }}>
          {categorias.map((cat) => (
            <div className="card" key={cat}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <SlidersHorizontal size={18} color="var(--color-navy)" />
                <span>{cat === 'RIESGO' ? 'Reglas de riesgo' : 'Notificaciones'}</span>
              </h3>
              {params.filter((p) => p.categoria === cat).map((p) => (
                <div className="form-group" key={p.clave}>
                  <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
                    <span>{ETIQUETA[p.clave] || p.clave}</span>
                    {p.origen === 'ENV' && <Badge type="PENDIENTE" text="Valor del .env" />}
                  </label>
                  <input
                    className="form-input"
                    type={p.tipo === 'int' ? 'number' : 'text'}
                    min={p.tipo === 'int' ? p.minimo : undefined}
                    max={p.tipo === 'int' ? p.maximo : undefined}
                    value={valores[p.clave] ?? ''}
                    onChange={(e) => setValores((prev) => ({ ...prev, [p.clave]: e.target.value }))}
                    required
                  />
                  <small style={{ color: 'var(--text-sec)' }}>
                    {p.descripcion}. {p.tipo === 'int' ? `Entre ${p.minimo} y ${p.maximo}.` : 'Números separados por coma.'}
                  </small>
                </div>
              ))}
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '20px' }}>
          <button type="submit" className="btn btn-primary" disabled={saving || cambiados.length === 0}>
            <Save size={16} />
            <span>{saving ? 'Guardando...' : `Guardar cambios${cambiados.length ? ` (${cambiados.length})` : ''}`}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
