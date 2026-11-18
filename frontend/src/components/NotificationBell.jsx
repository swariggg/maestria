import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Bell, CheckCheck } from 'lucide-react';
import { api } from '../services/api';

function haceCuanto(fecha) {
  const min = Math.round((Date.now() - new Date(fecha).getTime()) / 60000);
  if (min < 1) return 'ahora';
  if (min < 60) return `hace ${min} min`;
  const horas = Math.round(min / 60);
  if (horas < 24) return `hace ${horas} h`;
  const dias = Math.round(horas / 24);
  return dias === 1 ? 'ayer' : `hace ${dias} días`;
}

/** Campana con los avisos del usuario. Se actualiza sola cada minuto. */
export default function NotificationBell({ onNavigate }) {
  const [abierto, setAbierto] = useState(false);
  const [datos, setDatos] = useState({ no_leidas: 0, avisos: [] });
  const caja = useRef(null);

  const cargar = useCallback(async () => {
    try {
      setDatos(await api.getNotifications());
    } catch {
      // Sin conexión: se intenta en el siguiente ciclo
    }
  }, []);

  useEffect(() => {
    cargar();
    const id = setInterval(cargar, 60000);
    return () => clearInterval(id);
  }, [cargar]);

  useEffect(() => {
    if (!abierto) return undefined;
    const cerrar = (e) => { if (caja.current && !caja.current.contains(e.target)) setAbierto(false); };
    document.addEventListener('mousedown', cerrar);
    return () => document.removeEventListener('mousedown', cerrar);
  }, [abierto]);

  const abrirAviso = async (aviso) => {
    if (!aviso.leida) {
      try { await api.markNotificationRead(aviso.id); } catch { /* se reintenta al recargar */ }
    }
    setAbierto(false);
    cargar();
    if (onNavigate && aviso.destino) onNavigate(aviso.destino);
  };

  const leerTodas = async () => {
    try { await api.markAllNotificationsRead(); } finally { cargar(); }
  };

  return (
    <div className="notif-wrap" ref={caja}>
      <button
        type="button"
        className="btn btn-outline icon-circle"
        style={{ padding: 0, boxShadow: 'var(--shadow-soft)', border: 'none' }}
        onClick={() => { setAbierto(!abierto); if (!abierto) cargar(); }}
        title="Avisos"
        aria-label={`Avisos${datos.no_leidas ? `: ${datos.no_leidas} sin leer` : ''}`}
      >
        <Bell size={17} />
        {datos.no_leidas > 0 && <span className="notif-count">{datos.no_leidas > 99 ? '99+' : datos.no_leidas}</span>}
      </button>

      {abierto && (
        <div className="notif-panel" role="dialog" aria-label="Avisos">
          <div className="notif-head">
            <strong>Avisos</strong>
            {datos.no_leidas > 0 && (
              <button type="button" className="btn btn-outline" style={{ padding: '4px 10px', fontSize: '0.8rem' }} onClick={leerTodas}>
                <CheckCheck size={14} /> <span>Marcar todo como leído</span>
              </button>
            )}
          </div>
          {datos.avisos.length === 0 ? (
            <div style={{ padding: '28px 16px', textAlign: 'center', color: 'var(--text-sec)', fontSize: '0.9rem' }}>
              No tiene avisos por ahora.
            </div>
          ) : (
            datos.avisos.map((a) => (
              <button type="button" key={a.id} className={`notif-item ${a.leida ? '' : 'unread'}`} onClick={() => abrirAviso(a)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
                  <strong style={{ fontSize: '0.9rem' }}>{a.titulo}</strong>
                  <small style={{ whiteSpace: 'nowrap' }}>{haceCuanto(a.fecha)}</small>
                </div>
                {a.texto && <div style={{ fontSize: '0.83rem', color: 'var(--text-sec)', marginTop: '3px' }}>{a.texto}</div>}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
