import React from 'react';

export const LUCES = {
  ALTO: { color: '#C62828', apagado: '#F6D5D5', nombre: 'Rojo', texto: 'Riesgo alto' },
  MEDIO: { color: '#EAAA00', apagado: '#FBEFC7', nombre: 'Amarillo', texto: 'Riesgo medio' },
  BAJO: { color: '#2E7D32', apagado: '#D6EBD7', nombre: 'Verde', texto: 'Al día' },
};

/** Punto del semáforo para tablas y listas: solo se enciende el color del nivel. */
export function SemaforoPunto({ nivel, conTexto = true }) {
  const n = LUCES[nivel] ? nivel : 'BAJO';
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }} title={LUCES[n].texto}>
      <span style={{ display: 'inline-flex', gap: '3px', padding: '3px 5px', borderRadius: '999px', background: '#252533' }} aria-hidden="true">
        {['ALTO', 'MEDIO', 'BAJO'].map((k) => (
          <span key={k} style={{
            width: 10, height: 10, borderRadius: '50%',
            background: k === n ? LUCES[k].color : '#4A4A5A',
            boxShadow: k === n ? `0 0 6px ${LUCES[k].color}` : 'none',
          }} />
        ))}
      </span>
      {conTexto && <span style={{ fontWeight: 600, fontSize: '0.8rem', color: n === 'MEDIO' ? '#8A6500' : LUCES[n].color }}>{LUCES[n].texto}</span>}
    </span>
  );
}

/** Semáforo del panel: cuántos postulantes hay en cada color y qué regla los pone ahí. */
export function SemaforoPanel({ alto = 0, medio = 0, bajo = 0, reglas = {}, onVer }) {
  const total = alto + medio + bajo;
  const filas = [
    { k: 'ALTO', n: alto, regla: `${reglas.inactividad ?? 7} días sin actividad, ${reglas.intentos ?? 2} contactos sin respuesta o entregas vencidas sin subir` },
    { k: 'MEDIO', n: medio, regla: `Actividades sin entregar que vencen en ${reglas.porVencer ?? 5} días o menos, bajo avance o compromisos vencidos` },
    { k: 'BAJO', n: bajo, regla: 'Va al día con sus entregas' },
  ];
  return (
    <div style={{ display: 'flex', gap: '24px', alignItems: 'center', flexWrap: 'wrap' }}>
      <div style={{ background: '#252533', borderRadius: '28px', padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: '10px' }} aria-hidden="true">
        {filas.map(({ k, n }) => (
          <span key={k} style={{
            width: 38, height: 38, borderRadius: '50%',
            background: n > 0 ? LUCES[k].color : '#4A4A5A',
            boxShadow: n > 0 ? `0 0 14px ${LUCES[k].color}` : 'inset 0 2px 4px rgba(0,0,0,0.4)',
          }} />
        ))}
      </div>
      <div style={{ flex: '1 1 260px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {filas.map(({ k, n, regla }) => (
          <button key={k} type="button" onClick={onVer}
            style={{ display: 'flex', alignItems: 'center', gap: '14px', textAlign: 'left', border: 'none', background: LUCES[k].apagado, borderRadius: '14px', padding: '10px 14px', cursor: onVer ? 'pointer' : 'default', font: 'inherit', color: 'var(--text-main)' }}>
            <strong style={{ fontSize: '1.6rem', minWidth: '44px', color: k === 'MEDIO' ? '#8A6500' : LUCES[k].color }}>{n}</strong>
            <span style={{ flex: 1 }}>
              <strong style={{ display: 'block' }}>{LUCES[k].nombre}: {LUCES[k].texto}{total ? ` · ${Math.round((n / total) * 100)}%` : ''}</strong>
              <small style={{ color: 'var(--text-sec)' }}>{regla}</small>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
