import React from 'react';
import CourseArt, { paletaDelCurso } from './CourseArt';

/* Tarjeta de curso con figuras sencillas de fondo, estilo app de estudiante */
export default function CourseTile({ curso, selected, onClick, extra, children }) {
  const paleta = paletaDelCurso(curso);
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick?.(); } }}
      className={`course-tile tone-${paleta} ${selected ? 'selected' : ''}`}
      aria-pressed={selected}
    >
      <svg className="ct-shapes" viewBox="0 0 200 140" preserveAspectRatio="xMaxYMax slice" aria-hidden="true">
        <circle cx="170" cy="22" r="34" className="sh-a" />
        <path d="M110 150 C 120 90, 170 120, 160 70 S 210 40, 220 60" className="sh-b" />
        <circle cx="22" cy="128" r="7" className="sh-c" />
      </svg>
      <div className="ct-art"><CourseArt curso={curso} size={62} /></div>
      <div className="ct-body">
        <div className="ct-top">
          <span className="ct-code">{curso.codigo}</span>
          {extra}
        </div>
        <div className="ct-name">{curso.nombre}</div>
        {children}
      </div>
    </div>
  );
}
