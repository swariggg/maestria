import { useEffect } from 'react';

/*
 * Anima la entrada de tarjetas y secciones cuando aparecen en pantalla.
 * Funciona sobre las páginas existentes sin tocarlas: observa .card, .course-tile,
 * .table-responsive y [data-reveal] dentro de .page-body, también los que se agregan después.
 */
const SELECTOR = '.card, .course-tile, .table-responsive, [data-reveal]';

export default function useScrollReveal(rootSelector = '.page-body', deps = []) {
  useEffect(() => {
    const root = document.querySelector(rootSelector);
    if (!root || typeof IntersectionObserver === 'undefined') return undefined;
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined;

    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-in');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

    const preparar = (el) => {
      if (el.dataset.rv || el.closest('.modal-overlay')) return;
      el.dataset.rv = '1';
      // Escalonado: cada hermano entra un poco después del anterior
      const hermanos = el.parentElement ? Array.from(el.parentElement.children) : [];
      const i = Math.min(hermanos.indexOf(el), 8);
      el.style.setProperty('--rv-delay', `${Math.max(i, 0) * 60}ms`);
      el.classList.add('rv');
      io.observe(el);
    };

    root.querySelectorAll(SELECTOR).forEach(preparar);
    const mo = new MutationObserver((muts) => {
      muts.forEach((m) => m.addedNodes.forEach((n) => {
        if (n.nodeType !== 1) return;
        if (n.matches?.(SELECTOR)) preparar(n);
        n.querySelectorAll?.(SELECTOR).forEach(preparar);
      }));
    });
    mo.observe(root, { childList: true, subtree: true });

    return () => { io.disconnect(); mo.disconnect(); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
