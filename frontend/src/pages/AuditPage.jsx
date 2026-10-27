import React, { useState, useEffect } from 'react';
import { History, Shield, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import Badge from '../components/Badge';

export default function AuditPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadLogs = async () => {
    try {
      setLoading(true);
      const data = await api.getAuditLogs(100);
      setLogs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1>Bitácora de Auditoría y Trazabilidad</h1>
          <p style={{ color: 'var(--text-sec)' }}>
            Registro inmutable de transacciones, descargas, evaluaciones y accesos al sistema.
          </p>
        </div>

        <button className="btn btn-outline" onClick={loadLogs} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          <span>Actualizar Registros</span>
        </button>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center' }}>Cargando registros de auditoría...</div>
        ) : logs.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-sec)' }}>
            No hay eventos registrados en la bitácora.
          </div>
        ) : (
          <div className="table-responsive" style={{ border: 'none' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Fecha y Hora</th>
                  <th>Usuario Responsable</th>
                  <th>Operación / Acción</th>
                  <th>Entidad Afectada</th>
                  <th>ID Recurso</th>
                  <th>IP Origen</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td style={{ whiteSpace: 'nowrap' }}>
                      {new Date(log.fecha_creacion).toLocaleString()}
                    </td>
                    <td style={{ fontWeight: 600 }}>{log.usuario_nombre}</td>
                    <td>
                      <Badge type="PENDIENTE" text={log.accion} />
                    </td>
                    <td><code>{log.entidad}</code></td>
                    <td>{log.entidad_id || '-'}</td>
                    <td><small style={{ color: 'var(--text-sec)' }}>{log.ip_origen || '127.0.0.1'}</small></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
