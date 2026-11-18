import React, { useRef } from 'react';
import { UserRound, Target, Award } from 'lucide-react';
import CourseArt, { paletaDelCurso } from './CourseArt';

/*
 * Franja de color con el nombre del curso, al entrar a un curso.
 * La ilustración sobresale del recuadro y sigue al mouse con un leve efecto de profundidad.
 */
export default function CourseBanner({ curso, convocatoria }) {
  const ref = useRef(null);
  if (!curso) return null;
  const paleta = paletaDelCurso(curso);

  const mover = (e) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty('--mx', ((e.clientX - r.left) / r.width - 0.5).toFixed(3));
    el.style.setProperty('--my', ((e.clientY - r.top) / r.height - 0.5).toFixed(3));
  };
  const salir = () => {
    ref.current?.style.setProperty('--mx', 0);
    ref.current?.style.setProperty('--my', 0);
  };

  return (
    <section
      ref={ref}
      key={curso.id}
      className={`course-banner tone-${paleta}`}
      onMouseMove={mover}
      onMouseLeave={salir}
      aria-label={`Curso ${curso.nombre}`}
    >
      <div className="course-banner-bg" aria-hidden="true">
        <span className="cb-ring" />
        <span className="cb-dot d1" />
        <span className="cb-dot d2" />
        <span className="cb-ghost">{curso.codigo}</span>
      </div>

      <div className="course-banner-text">
        <div className="cb-chips">
          <span className="cb-chip">{curso.codigo}</span>
          {convocatoria && <span className="cb-chip ghost">{convocatoria.codigo}</span>}
        </div>
        <h1 className="cb-title">{curso.nombre}</h1>
        <div className="cb-meta">
          <span><UserRound size={15} /> {curso.tutor_nombre || 'Tutor por asignar'}</span>
          <span><Award size={15} /> {curso.ponderacion_total ?? 100} puntos</span>
          <span><Target size={15} /> Aprueba con {curso.nota_minima ?? 70}/100</span>
        </div>
      </div>

      <div className="course-banner-art" aria-hidden="true">
        <span className="cb-blob" />
        <CourseArt curso={curso} size={210} className="cb-art" />
        <span className="cb-spark s1" />
        <span className="cb-spark s2" />
        <span className="cb-spark s3" />
      </div>
    </section>
  );
}
