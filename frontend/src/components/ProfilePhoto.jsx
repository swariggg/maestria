import React, { useState, useEffect, useRef } from 'react';
import { Camera, Trash2 } from 'lucide-react';
import { api } from '../services/api';

export function iniciales(nombre = '') {
  return nombre.replace(/\(.*?\)/g, '').split(' ').filter((p) => p && !p.endsWith('.'))
    .slice(0, 2).map((p) => p[0].toUpperCase()).join('');
}

/**
 * Foto de perfil. Se pide con la sesión (no es pública) y, si no hay foto, se muestran las iniciales.
 * Con editable=true deja subir o quitar la foto propia.
 */
export default function ProfilePhoto({ usuarioId, nombre, tieneFoto, size = 96, editable = false, onChange }) {
  const [url, setUrl] = useState(null);
  const [error, setError] = useState(null);
  const [subiendo, setSubiendo] = useState(false);
  const input = useRef(null);

  useEffect(() => {
    let vivo = true;
    let actual = null;
    if (tieneFoto && usuarioId) {
      api.getPhoto(usuarioId).then((blob) => {
        if (!vivo) return;
        actual = URL.createObjectURL(blob);
        setUrl(actual);
      }).catch(() => vivo && setUrl(null));
    } else {
      setUrl(null);
    }
    return () => { vivo = false; if (actual) URL.revokeObjectURL(actual); };
  }, [usuarioId, tieneFoto]);

  const subir = async (e) => {
    const archivo = e.target.files?.[0];
    e.target.value = '';
    if (!archivo) return;
    setError(null);
    if (archivo.size > 2 * 1024 * 1024) { setError('La foto debe pesar menos de 2 MB.'); return; }
    setSubiendo(true);
    try {
      const fd = new FormData();
      fd.append('file', archivo);
      await api.uploadPhoto(fd);
      onChange && onChange(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubiendo(false);
    }
  };

  const quitar = async () => {
    setError(null);
    try { await api.deletePhoto(); onChange && onChange(false); } catch (err) { setError(err.message); }
  };

  const circulo = {
    width: size, height: size, borderRadius: '50%', flexShrink: 0, overflow: 'hidden',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: 'var(--color-cream)', color: 'var(--color-burgundy)', fontWeight: 700,
    fontSize: Math.round(size / 2.8), border: '3px solid #FFFFFF', boxShadow: 'var(--shadow-soft)',
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
      <div style={circulo}>
        {url ? <img src={url} alt={`Foto de ${nombre}`} style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : iniciales(nombre)}
      </div>
      {editable && (
        <div>
          <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={subir} />
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button type="button" className="btn btn-outline" style={{ padding: '6px 12px' }} disabled={subiendo} onClick={() => input.current?.click()}>
              <Camera size={15} /> <span>{subiendo ? 'Subiendo...' : tieneFoto ? 'Cambiar foto' : 'Subir foto'}</span>
            </button>
            {tieneFoto && (
              <button type="button" className="btn btn-outline" style={{ padding: '6px 12px' }} onClick={quitar}>
                <Trash2 size={15} /> <span>Quitar</span>
              </button>
            )}
          </div>
          <small style={{ display: 'block', color: 'var(--text-sec)', marginTop: '6px' }}>JPG, PNG o WEBP, hasta 2 MB.</small>
          {error && <small style={{ display: 'block', color: 'var(--status-danger-text)', marginTop: '4px' }}>{error}</small>}
        </div>
      )}
    </div>
  );
}
