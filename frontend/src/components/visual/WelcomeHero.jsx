import React from 'react';
import { ChevronDown, ArrowUpRight } from 'lucide-react';

const TEXTOS = {
  POSTULANTE: {
    saludo: 'Tu camino al posgrado',
    titulo: ['Prepárate,', 'avanza y', 'reinventa', 'tu futuro'],
    resumen: 'Aquí ves tus cursos preparatorios, tus entregas pendientes y los avisos de tus tutores.',
    chips: ['Cursos preparatorios', 'Entregas', 'Certificados'],
  },
  TUTOR: {
    saludo: 'Panel del tutor',
    titulo: ['Acompaña', 'a cada', 'postulante', 'paso a paso'],
    resumen: 'Revisa evidencias, califica con rúbrica y atiende a quienes están en riesgo.',
    chips: ['Evidencias por revisar', 'Rúbricas', 'Seguimiento'],
  },
  COORDINADOR: {
    saludo: 'Coordinación académica',
    titulo: ['Todo el', 'proceso', 'preparatorio', 'en un vistazo'],
    resumen: 'Convocatorias, cursos, riesgos y avance de cada cohorte en un solo lugar.',
    chips: ['Convocatorias', 'Riesgos', 'Reportes'],
  },
  ADMIN: {
    saludo: 'Administración',
    titulo: ['Gestiona', 'la maestría', 'con datos', 'claros'],
    resumen: 'Usuarios, parámetros, auditoría y el estado global de los cursos preparatorios.',
    chips: ['Usuarios', 'Configuración', 'Auditoría'],
  },
};

function primerNombre(nombre = '') {
  return nombre.replace(/\(.*?\)/g, '').split(' ').find((p) => p && !p.endsWith('.')) || '';
}

/*
 * Portada del panel.
 * - Postulante: una sola imagen del campus a pantalla casi completa antes del resto (se baja con la flecha).
 * - Personal UIDE: fondo simple, mezcla de tamaños de texto y la imagen al lado con tarjetas flotantes.
 */
export default function WelcomeHero({ user, children }) {
  const rol = user?.rol?.codigo || 'POSTULANTE';
  const t = TEXTOS[rol] || TEXTOS.POSTULANTE;
  const nombre = primerNombre(user?.nombre_completo);

  if (rol === 'POSTULANTE') {
    const bajar = () => document.getElementById('panel-contenido')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return (
      <>
        <section className="hero-photo" aria-label="Bienvenida">
          <img src="/campus-uide.jpg" alt="Campus de la UIDE en Quito" className="hero-photo-img" />
          <div className="hero-photo-shade" aria-hidden="true" />
          <div className="hero-photo-content">
            <span className="hero-kicker">{t.saludo}</span>
            <h1 className="hero-title">
              Hola, {nombre}.
              <span className="hero-title-sub">{t.titulo.join(' ')}</span>
            </h1>
            <p className="hero-lead">{t.resumen}</p>
            <div className="hero-actions">{children}</div>
          </div>
          <button type="button" className="hero-scroll" onClick={bajar} aria-label="Ver mi panel">
            <span>Ver mi panel</span>
            <ChevronDown size={18} />
          </button>
        </section>
        <div id="panel-contenido" className="anchor-offset" />
      </>
    );
  }

  return (
    <section className="hero-split" aria-label="Bienvenida">
      <div className="hero-split-text">
        <span className="hero-kicker">{t.saludo} · Hola, {nombre}</span>
        <h1 className="hero-mix">
          <span className="w-xl">{t.titulo[0]}</span>{' '}
          <span className="w-md">{t.titulo[1]}</span>{' '}
          <span className="w-xl accent">{t.titulo[2]}</span>{' '}
          <span className="w-sm">{t.titulo[3]}</span>
        </h1>
        <p className="hero-lead">{t.resumen}</p>
        <div className="hero-chips">
          {t.chips.map((c) => <span key={c} className="chip-soft">{c}</span>)}
        </div>
        {children && <div className="hero-actions">{children}</div>}
      </div>

      <div className="hero-split-media">
        <div className="hero-media-card">
          <img src="/campus-uide.jpg" alt="Campus de la UIDE en Quito" />
          <div className="hero-media-glass">
            <div>
              <strong>Cursos preparatorios</strong>
              <small>de posgrado UIDE</small>
            </div>
            <span className="hero-media-arrow"><ArrowUpRight size={18} /></span>
          </div>
        </div>
        <img src="/uide-isotipo.svg" alt="" className="hero-float-logo" aria-hidden="true" />
      </div>
    </section>
  );
}
