import React, { useState, useEffect } from 'react';
import { FileText, FileSpreadsheet, Download, CheckCircle2, Route, Award } from 'lucide-react';
import { api } from '../services/api';
import { saveBlob } from '../utils/download';

const hoy = () => new Date().toISOString().slice(0, 10);

export default function ReportsPage({ user }) {
  const role = user?.rol?.codigo;
  const esStaff = ['ADMIN', 'COORDINADOR', 'TUTOR'].includes(role);

  const [programs, setPrograms] = useState([]);
  const [selectedProgId, setSelectedProgId] = useState('');
  const [applicants, setApplicants] = useState([]);
  const [selectedInscId, setSelectedInscId] = useState('');
  const [misInscripciones, setMisInscripciones] = useState([]);
  const [trazAlcance, setTrazAlcance] = useState('postulante'); // postulante | programa
  const [trazProgId, setTrazProgId] = useState('');
  const [downloading, setDownloading] = useState(null);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        if (esStaff) {
          const [progs, apps] = await Promise.all([api.getPrograms(), api.getApplicants()]);
          setPrograms(progs);
          setApplicants(apps);
          if (apps.length > 0) setSelectedInscId(apps[0].id);
        } else {
          const mias = await api.getMyEnrollments();
          setMisInscripciones(mias);
          if (mias.length > 0) setSelectedInscId(mias[0].id);
        }
      } catch (err) {
        setMessage({ type: 'error', text: err.message });
      }
    };
    load();
  }, []);

  const descargar = async (clave, peticion, nombre, texto) => {
    try {
      setDownloading(clave);
      setMessage(null);
      saveBlob(await peticion(), nombre);
      setMessage({ type: 'success', text: texto });
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setDownloading(null);
    }
  };

  const trazParams = () => (trazAlcance === 'postulante'
    ? { inscripcion_id: selectedInscId }
    : (trazProgId ? { programa_id: trazProgId } : {}));

  const selectorProgramas = (valor, onChange) => (
    <select className="form-select" value={valor} onChange={(e) => onChange(e.target.value)}>
      <option value="">Todos los programas autorizados</option>
      {programs.map((p) => (
        <option key={p.id} value={p.id}>{p.codigo} - {p.nombre}</option>
      ))}
    </select>
  );

  const selectorPostulantes = (
    <select className="form-select" value={selectedInscId} onChange={(e) => setSelectedInscId(e.target.value)}>
      {applicants.map((a) => (
        <option key={a.id} value={a.id}>{a.nombre_completo} (CI: {a.cedula}) - {a.programa_codigo}</option>
      ))}
    </select>
  );

  const icono = (Icon, fondo, color) => (
    <div style={{ display: 'inline-flex', background: fondo, padding: '12px', borderRadius: '16px', marginBottom: '16px' }}>
      <Icon size={28} color={color} />
    </div>
  );

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1>Generación y Exportación de Reportes</h1>
        <p style={{ color: 'var(--text-sec)' }}>
          Matrices consolidadas, informes individuales e informes de trazabilidad en PDF y Excel.
        </p>
      </div>

      {message && (
        <div className={message.type === 'error' ? 'notice-danger' : 'notice-success'} style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          {message.type === 'success' && <CheckCircle2 size={18} />}
          <span>{message.text}</span>
        </div>
      )}

      <div className="grid-cols-2">
        {esStaff && (
          <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              {icono(FileSpreadsheet, 'var(--color-sec)', 'var(--color-navy)')}
              <h3>Matriz Consolidada de Seguimiento</h3>
              <p style={{ color: 'var(--text-sec)', margin: '8px 0 16px' }}>
                {role === 'TUTOR' ? 'Sus postulantes asignados' : 'Todos los postulantes'} con avance, actividades pendientes, días que faltan para el fin del preparatorio,
                tutor, número de contactos, estado y nivel de riesgo.
              </p>
              <div className="form-group">
                <label className="form-label">Filtrar por programa</label>
                {selectorProgramas(selectedProgId, setSelectedProgId)}
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '20px' }}>
              <button
                className="btn btn-secondary"
                disabled={!!downloading}
                onClick={() => descargar('mx', () => api.downloadConsolidatedExcel(selectedProgId || undefined), `matriz_seguimiento_uide_${hoy()}.xlsx`, 'Matriz consolidada en Excel generada.')}
              >
                <Download size={16} />
                <span>{downloading === 'mx' ? 'Generando...' : 'Excel'}</span>
              </button>
              <button
                className="btn btn-primary"
                disabled={!!downloading}
                onClick={() => descargar('mp', () => api.downloadConsolidatedPdf(selectedProgId || undefined), `matriz_seguimiento_uide_${hoy()}.pdf`, 'Matriz consolidada en PDF generada.')}
              >
                <Download size={16} />
                <span>{downloading === 'mp' ? 'Generando...' : 'PDF'}</span>
              </button>
            </div>
          </div>
        )}

        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            {icono(FileText, 'var(--color-primary)', 'var(--color-primary-text)')}
            <h3>Informe Individual de Seguimiento (PDF)</h3>
            <p style={{ color: 'var(--text-sec)', margin: '8px 0 16px' }}>
              Documento formal con encabezado de la UIDE, calificaciones por actividad, contactos del tutor y nivel de riesgo.
            </p>
            {esStaff && (
              <div className="form-group">
                <label className="form-label">Postulante</label>
                {selectorPostulantes}
              </div>
            )}
            {!esStaff && misInscripciones.length > 1 && (
              <div className="form-group">
                <label className="form-label">Inscripción</label>
                <select className="form-select" value={selectedInscId} onChange={(e) => setSelectedInscId(e.target.value)}>
                  {misInscripciones.map((i) => <option key={i.id} value={i.id}>{i.programa_nombre} · {i.convocatoria_nombre}</option>)}
                </select>
              </div>
            )}
          </div>
          <button
            className="btn btn-primary"
            style={{ width: '100%', marginTop: '20px' }}
            disabled={!!downloading || !selectedInscId}
            onClick={() => descargar('ind', () => api.downloadIndividualPdf(selectedInscId), `informe_individual_uide_${selectedInscId}.pdf`, 'Informe individual en PDF generado.')}
          >
            <Download size={16} />
            <span>{downloading === 'ind' ? 'Generando PDF...' : 'Descargar Informe en PDF'}</span>
          </button>
        </div>

        {(() => {
          // Certificado: el postulante descarga el suyo; el personal, el del postulante elegido
          const insc = esStaff
            ? applicants.find((a) => String(a.id) === String(selectedInscId))
            : misInscripciones.find((i) => String(i.id) === String(selectedInscId));
          if (!insc || insc.estado_proceso !== 'APROBADO') return null;
          return (
            <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                {icono(Award, 'var(--status-success-bg)', 'var(--status-success-text)')}
                <h3>Certificado de aprobación</h3>
                <p style={{ color: 'var(--text-sec)', margin: '8px 0 16px' }}>
                  PDF con el logo de la UIDE, los datos del postulante, sus notas, la firma de coordinación y un código
                  de verificación.
                </p>
              </div>
              <button
                className="btn btn-primary"
                style={{ width: '100%', marginTop: '20px' }}
                disabled={!!downloading}
                onClick={() => descargar('cert', () => api.downloadCertificate(insc.id), `certificado_${insc.cedula || insc.id}.pdf`, 'Certificado generado.')}
              >
                <Download size={16} />
                <span>{downloading === 'cert' ? 'Generando...' : 'Descargar certificado'}</span>
              </button>
            </div>
          );
        })()}

        {esStaff && (
          <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              {icono(Route, 'var(--color-sec)', 'var(--color-navy)')}
              <h3>Informe de Trazabilidad</h3>
              <p style={{ color: 'var(--text-sec)', margin: '8px 0 16px' }}>
                Una fila por seguimiento: número, fecha, responsable, tipo de contacto, acción, resultado, respuesta del
                postulante, compromisos, próxima acción, estado final y evidencia asociada.
              </p>
              <div className="form-group">
                <label className="form-label">Alcance</label>
                <select className="form-select" value={trazAlcance} onChange={(e) => setTrazAlcance(e.target.value)}>
                  <option value="postulante">Un postulante</option>
                  <option value="programa">{role === 'TUTOR' ? 'Todos mis postulantes' : 'Por programa'}</option>
                </select>
              </div>
              {trazAlcance === 'postulante' ? (
                <div className="form-group">
                  <label className="form-label">Postulante</label>
                  {selectorPostulantes}
                </div>
              ) : role !== 'TUTOR' && (
                <div className="form-group">
                  <label className="form-label">Programa</label>
                  {selectorProgramas(trazProgId, setTrazProgId)}
                </div>
              )}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '20px' }}>
              <button
                className="btn btn-secondary"
                disabled={!!downloading || (trazAlcance === 'postulante' && !selectedInscId)}
                onClick={() => descargar('tx', () => api.downloadTraceability('excel', trazParams()), `trazabilidad_uide_${hoy()}.xlsx`, 'Informe de trazabilidad en Excel generado.')}
              >
                <Download size={16} />
                <span>{downloading === 'tx' ? 'Generando...' : 'Excel'}</span>
              </button>
              <button
                className="btn btn-primary"
                disabled={!!downloading || (trazAlcance === 'postulante' && !selectedInscId)}
                onClick={() => descargar('tp', () => api.downloadTraceability('pdf', trazParams()), `trazabilidad_uide_${hoy()}.pdf`, 'Informe de trazabilidad en PDF generado.')}
              >
                <Download size={16} />
                <span>{downloading === 'tp' ? 'Generando...' : 'PDF'}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
