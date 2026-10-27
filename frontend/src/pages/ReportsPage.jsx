import React, { useState, useEffect } from 'react';
import { FileText, FileSpreadsheet, Download, Filter, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';

export default function ReportsPage({ user }) {
  const [programs, setPrograms] = useState([]);
  const [selectedProgId, setSelectedProgId] = useState('');
  const [applicants, setApplicants] = useState([]);
  const [selectedInscId, setSelectedInscId] = useState('');
  const [downloading, setDownloading] = useState(false);
  const [successMsg, setSuccessMsg] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const progs = await api.getPrograms();
        setPrograms(progs);
        const apps = await api.getApplicants();
        setApplicants(apps);
        if (apps.length > 0) setSelectedInscId(apps[0].id);
      } catch (err) {
        console.error(err);
      }
    };
    load();
  }, []);

  const handleDownloadExcel = async () => {
    try {
      setDownloading(true);
      setSuccessMsg(null);
      const blob = await api.downloadConsolidatedExcel(selectedProgId || undefined);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `matriz_seguimiento_uide_${new Date().toISOString().slice(0, 10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setSuccessMsg('Matriz consolidada en formato Excel (.xlsx) generada exitosamente.');
    } catch (err) {
      alert(`Error generando Excel: ${err.message}`);
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!selectedInscId) return;
    try {
      setDownloading(true);
      setSuccessMsg(null);
      const blob = await api.downloadIndividualPdf(selectedInscId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `informe_individual_uide_${selectedInscId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setSuccessMsg('Informe individual en formato PDF generado exitosamente con membrete institucional.');
    } catch (err) {
      alert(`Error generando PDF: ${err.message}`);
    } finally {
      setDownloading(false);
    }
  };

  const role = user?.rol?.codigo;

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1>Generación y Exportación de Reportes</h1>
        <p style={{ color: 'var(--text-sec)' }}>
          Descarga de matrices consolidadas e informes individuales auditables en PDF y Excel nativos.
        </p>
      </div>

      {successMsg && (
        <div style={{
          backgroundColor: 'var(--color-comp)',
          color: 'var(--color-comp-text)',
          padding: '14px 20px',
          borderRadius: '14px',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontWeight: 500
        }}>
          <CheckCircle2 size={18} />
          <span>{successMsg}</span>
        </div>
      )}

      <div className="grid-cols-2">
        {/* Reporte Consolidado Excel */}
        {['ADMIN', 'COORDINADOR'].includes(role) && (
          <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div style={{
                display: 'inline-flex',
                background: 'var(--color-sec)',
                padding: '12px',
                borderRadius: '16px',
                marginBottom: '16px'
              }}>
                <FileSpreadsheet size={28} color="#1E3A8A" />
              </div>
              <h3>Matriz Consolidada de Seguimiento (Excel)</h3>
              <p style={{ color: 'var(--text-sec)', margin: '8px 0 16px' }}>
                Genera un libro Microsoft Excel (.xlsx) con todos los postulantes, avance porcentual, días restantes, tutores asignados, número de llamadas/contactos y clasificación de riesgo con formato condicional.
              </p>

              <div className="form-group">
                <label className="form-label">Filtrar por Programa</label>
                <select
                  className="form-select"
                  value={selectedProgId}
                  onChange={(e) => setSelectedProgId(e.target.value)}
                >
                  <option value="">Todos los programas autorizados</option>
                  {programs.map((p) => (
                    <option key={p.id} value={p.id}>{p.codigo} - {p.nombre}</option>
                  ))}
                </select>
              </div>
            </div>

            <button
              onClick={handleDownloadExcel}
              className="btn btn-secondary"
              style={{ width: '100%', marginTop: '20px' }}
              disabled={downloading}
            >
              <Download size={16} />
              <span>{downloading ? 'Generando libro Excel...' : 'Descargar Matriz en Excel (.xlsx)'}</span>
            </button>
          </div>
        )}

        {/* Reporte Individual PDF */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{
              display: 'inline-flex',
              background: 'var(--color-primary)',
              padding: '12px',
              borderRadius: '16px',
              marginBottom: '16px'
            }}>
              <FileText size={28} color="#701A48" />
            </div>
            <h3>Informe Individual de Seguimiento (PDF)</h3>
            <p style={{ color: 'var(--text-sec)', margin: '8px 0 16px' }}>
              Genera un documento PDF formal con encabezado de la UIDE, desglose de calificaciones por actividad, historial cronológico de contactos del tutor y resumen de nivel de riesgo.
            </p>

            {['ADMIN', 'COORDINADOR', 'TUTOR'].includes(role) && (
              <div className="form-group">
                <label className="form-label">Seleccionar Expediente del Postulante</label>
                <select
                  className="form-select"
                  value={selectedInscId}
                  onChange={(e) => setSelectedInscId(e.target.value)}
                >
                  {applicants.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.nombre_completo} (CI: {a.cedula}) - {a.programa_codigo}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <button
            onClick={handleDownloadPdf}
            className="btn btn-primary"
            style={{ width: '100%', marginTop: '20px' }}
            disabled={downloading}
          >
            <Download size={16} />
            <span>{downloading ? 'Generando PDF...' : 'Descargar Informe en PDF'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
