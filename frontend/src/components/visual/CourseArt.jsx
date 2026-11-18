import React from 'react';

/*
 * Ilustraciones sencillas para cada curso, en los colores del manual de marca.
 * Se elige una según palabras del nombre del curso (seguridad → candado, etc.).
 * Trazo azul marino, rellenos dorado / guinda / blanco, como los iconos de dos tonos.
 */

const NAVY = '#002D72';
const GOLD = '#EAAA00';
const UIDE = '#910048';
const CREAM = '#FBF1D6';

const TEMAS = [
  { id: 'candado', palabras: ['segur', 'ciber', 'hack', 'riesgo', 'protec', 'auditor'] },
  { id: 'codigo', palabras: ['program', 'software', 'desarroll', 'código', 'codigo', 'algoritm', 'web', 'python', 'java'] },
  { id: 'datos', palabras: ['dato', 'base', 'sql', 'big data', 'información', 'informacion', 'intelig'] },
  { id: 'grafico', palabras: ['estad', 'matem', 'cálculo', 'calculo', 'finan', 'econ', 'contab', 'cuantit', 'álgebra', 'algebra'] },
  { id: 'globo', palabras: ['redes', 'telecom', 'internac', 'comerc', 'idioma', 'inglés', 'ingles', 'nube', 'cloud', 'marketing'] },
  { id: 'engranaje', palabras: ['gestión', 'gestion', 'proceso', 'admin', 'proyecto', 'industr', 'operac', 'calidad', 'ingenier'] },
  { id: 'balanza', palabras: ['derech', 'legal', 'ética', 'etica', 'norma', 'jurid', 'polít', 'polit'] },
  { id: 'lupa', palabras: ['investig', 'metodol', 'tesis', 'científ', 'cientif', 'análisis', 'analisis'] },
  { id: 'corazon', palabras: ['salud', 'médic', 'medic', 'enferm', 'psico', 'nutri', 'bienestar'] },
];

export function temaDelCurso(curso) {
  const texto = `${curso?.nombre || ''} ${curso?.codigo || ''} ${curso?.descripcion || ''}`.toLowerCase();
  const tema = TEMAS.find((t) => t.palabras.some((p) => texto.includes(p)));
  return tema ? tema.id : 'libro';
}

/* Paleta por curso: se reparte de forma estable según el id */
const PALETAS = ['uide', 'navy', 'gold'];
export function paletaDelCurso(curso) {
  const n = Number(curso?.id) || String(curso?.codigo || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  return PALETAS[Math.abs(n) % PALETAS.length];
}

const sombra = <ellipse cx="80" cy="150" rx="46" ry="6" fill={NAVY} opacity="0.18" />;

const ARTES = {
  candado: (
    <>
      {sombra}
      <path d="M50 70 V50 a30 30 0 0 1 60 0 V70" fill="none" stroke={NAVY} strokeWidth="12" strokeLinecap="round" />
      <path d="M50 70 V50 a30 30 0 0 1 60 0 V70" fill="none" stroke="#C9D3E3" strokeWidth="5" strokeLinecap="round" />
      <rect x="30" y="66" width="100" height="78" rx="18" fill={GOLD} stroke={NAVY} strokeWidth="5" />
      <rect x="38" y="74" width="30" height="62" rx="10" fill="#FFFFFF" opacity="0.35" />
      <circle cx="80" cy="99" r="11" fill={NAVY} />
      <rect x="75" y="104" width="10" height="20" rx="5" fill={NAVY} />
    </>
  ),
  codigo: (
    <>
      {sombra}
      <rect x="18" y="30" width="124" height="104" rx="16" fill="#FFFFFF" stroke={NAVY} strokeWidth="5" />
      <path d="M18 46 a16 16 0 0 1 16 -16 h92 a16 16 0 0 1 16 16 v6 H18 z" fill={NAVY} />
      <circle cx="34" cy="41" r="4" fill={GOLD} /><circle cx="47" cy="41" r="4" fill="#FFFFFF" /><circle cx="60" cy="41" r="4" fill={UIDE} />
      <path d="M58 76 L42 92 L58 108" fill="none" stroke={UIDE} strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M102 76 L118 92 L102 108" fill="none" stroke={UIDE} strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M88 70 L72 114" stroke={GOLD} strokeWidth="8" strokeLinecap="round" />
    </>
  ),
  datos: (
    <>
      {sombra}
      {[100, 72, 44].map((y, i) => (
        <g key={y}>
          <path d={`M32 ${y} v22 a48 14 0 0 0 96 0 v-22`} fill={i === 1 ? '#FFFFFF' : GOLD} stroke={NAVY} strokeWidth="5" />
          <ellipse cx="80" cy={y} rx="48" ry="14" fill={i === 2 ? UIDE : CREAM} stroke={NAVY} strokeWidth="5" />
        </g>
      ))}
      <circle cx="112" cy="84" r="4" fill={NAVY} /><circle cx="112" cy="112" r="4" fill={NAVY} />
    </>
  ),
  grafico: (
    <>
      {sombra}
      <rect x="20" y="24" width="120" height="116" rx="18" fill="#FFFFFF" stroke={NAVY} strokeWidth="5" />
      <rect x="36" y="94" width="18" height="32" rx="5" fill={CREAM} stroke={NAVY} strokeWidth="4" />
      <rect x="62" y="74" width="18" height="52" rx="5" fill={GOLD} stroke={NAVY} strokeWidth="4" />
      <rect x="88" y="58" width="18" height="68" rx="5" fill={UIDE} stroke={NAVY} strokeWidth="4" />
      <path d="M36 74 L68 52 L90 60 L124 36" fill="none" stroke={NAVY} strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="124" cy="36" r="7" fill={GOLD} stroke={NAVY} strokeWidth="4" />
    </>
  ),
  globo: (
    <>
      {sombra}
      <circle cx="80" cy="82" r="58" fill="#FFFFFF" stroke={NAVY} strokeWidth="5" />
      <path d="M50 42 q14 10 8 24 q-6 12 8 18 q14 6 6 22 q-6 10 4 22" fill="none" stroke={GOLD} strokeWidth="14" strokeLinecap="round" opacity="0.9" />
      <ellipse cx="80" cy="82" rx="24" ry="58" fill="none" stroke={NAVY} strokeWidth="4" />
      <path d="M24 70 h112 M24 96 h112" stroke={NAVY} strokeWidth="4" />
      <circle cx="122" cy="40" r="14" fill={UIDE} stroke={NAVY} strokeWidth="4" />
      <circle cx="122" cy="40" r="5" fill="#FFFFFF" />
    </>
  ),
  engranaje: (
    <>
      {sombra}
      <g transform="translate(66 80)">
        {Array.from({ length: 8 }).map((_, i) => (
          <rect key={i} x="-9" y="-56" width="18" height="22" rx="5" fill={GOLD} stroke={NAVY} strokeWidth="4" transform={`rotate(${i * 45})`} />
        ))}
        <circle r="40" fill={GOLD} stroke={NAVY} strokeWidth="5" />
        <circle r="16" fill="#FFFFFF" stroke={NAVY} strokeWidth="5" />
      </g>
      <g transform="translate(122 118)">
        {Array.from({ length: 6 }).map((_, i) => (
          <rect key={i} x="-6" y="-30" width="12" height="14" rx="4" fill={UIDE} stroke={NAVY} strokeWidth="3.5" transform={`rotate(${i * 60})`} />
        ))}
        <circle r="21" fill={UIDE} stroke={NAVY} strokeWidth="4" />
        <circle r="8" fill="#FFFFFF" stroke={NAVY} strokeWidth="4" />
      </g>
    </>
  ),
  balanza: (
    <>
      {sombra}
      <rect x="74" y="34" width="12" height="104" rx="6" fill={NAVY} />
      <rect x="48" y="132" width="64" height="12" rx="6" fill={NAVY} />
      <path d="M28 50 H132" stroke={NAVY} strokeWidth="7" strokeLinecap="round" />
      <circle cx="80" cy="36" r="9" fill={GOLD} stroke={NAVY} strokeWidth="4" />
      <path d="M36 52 L20 92 M36 52 L52 92 M124 52 L108 92 M124 52 L140 92" stroke={NAVY} strokeWidth="3" />
      <path d="M16 92 h40 a20 16 0 0 1 -40 0 z" fill={GOLD} stroke={NAVY} strokeWidth="4" />
      <path d="M104 92 h40 a20 16 0 0 1 -40 0 z" fill={UIDE} stroke={NAVY} strokeWidth="4" />
    </>
  ),
  lupa: (
    <>
      {sombra}
      <rect x="22" y="26" width="84" height="108" rx="12" fill="#FFFFFF" stroke={NAVY} strokeWidth="5" />
      <path d="M36 50 h50 M36 66 h40 M36 82 h46" stroke="#C9D3E3" strokeWidth="6" strokeLinecap="round" />
      <path d="M110 112 L138 140" stroke={NAVY} strokeWidth="14" strokeLinecap="round" />
      <circle cx="94" cy="94" r="30" fill={CREAM} fillOpacity="0.85" stroke={NAVY} strokeWidth="7" />
      <path d="M80 86 a16 16 0 0 1 14 -10" fill="none" stroke={GOLD} strokeWidth="6" strokeLinecap="round" />
    </>
  ),
  corazon: (
    <>
      {sombra}
      <path d="M80 136 C20 96 18 58 40 42 C58 30 74 40 80 54 C86 40 102 30 120 42 C142 58 140 96 80 136 z" fill={UIDE} stroke={NAVY} strokeWidth="5" />
      <path d="M30 86 h28 l8 -16 l12 30 l10 -22 l6 8 h36" fill="none" stroke="#FFFFFF" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="54" cy="56" r="6" fill="#FFFFFF" opacity="0.5" />
    </>
  ),
  libro: (
    <>
      {sombra}
      <path d="M80 44 C62 32 38 30 18 34 V128 C38 124 62 126 80 138 z" fill="#FFFFFF" stroke={NAVY} strokeWidth="5" strokeLinejoin="round" />
      <path d="M80 44 C98 32 122 30 142 34 V128 C122 124 98 126 80 138 z" fill={GOLD} stroke={NAVY} strokeWidth="5" strokeLinejoin="round" />
      <path d="M32 58 C46 56 58 58 68 64 M32 76 C46 74 58 76 68 82 M32 94 C46 92 58 94 68 100" stroke="#C9D3E3" strokeWidth="5" strokeLinecap="round" fill="none" />
      <path d="M104 30 v40 l9 -8 l9 8 v-42" fill={UIDE} stroke={NAVY} strokeWidth="4" strokeLinejoin="round" />
    </>
  ),
};

export default function CourseArt({ curso, tema, size = 160, className = '' }) {
  const id = tema || temaDelCurso(curso);
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 160 160"
      role="img"
      aria-hidden="true"
      focusable="false"
    >
      {ARTES[id] || ARTES.libro}
    </svg>
  );
}
