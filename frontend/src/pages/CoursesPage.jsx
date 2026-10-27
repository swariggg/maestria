import React, { useState, useEffect } from 'react';
import { BookOpen, Plus, Calendar, CheckSquare, Layers, Award } from 'lucide-react';
import { api } from '../services/api';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

export default function CoursesPage({ user }) {
  const [programs, setPrograms] = useState([]);
  const [selectedProg, setSelectedProg] = useState(null);
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  // Modal Crear Actividad
  const [showAddActModal, setShowAddActModal] = useState(false);
  const [actTitle, setActTitle] = useState('');
  const [actType, setActType] = useState('INDIVIDUAL');
  const [actInstructions, setActInstructions] = useState('');
  const [actWeight, setActWeight] = useState(25);
  const [actDeadline, setActDeadline] = useState('');
  const [actError, setActError] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const progs = await api.getPrograms();
      setPrograms(progs);
      if (progs.length > 0) {
        setSelectedProg(progs[0]);
        const crs = await api.getCourses();
        setCourses(crs);
        if (crs.length > 0) {
          setSelectedCourse(crs[0]);
          const acts = await api.getActivities(crs[0].id);
          setActivities(acts);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelectCourse = async (crs) => {
    setSelectedCourse(crs);
    try {
      const acts = await api.getActivities(crs.id);
      setActivities(acts);
    } catch (err) {
      alert(`Error al cargar actividades: ${err.message}`);
    }
  };

  const handleCreateActivity = async (e) => {
    e.preventDefault();
    setActError(null);

    // Calcular suma actual de ponderaciones
    const sumaActual = activities.reduce((acc, a) => acc + parseFloat(a.ponderacion || 0), 0);
    if (sumaActual + parseFloat(actWeight) > 100) {
      setActError(`La ponderación total superaría el 100%. Suma actual: ${sumaActual}%, intento: +${actWeight}%.`);
      return;
    }

    try {
      await api.createActivity({
        curso_id: selectedCourse.id,
        titulo: actTitle,
        tipo: actType,
        instrucciones: actInstructions,
        fecha_apertura: new Date().toISOString(),
        fecha_limite: new Date(actDeadline).toISOString(),
        ponderacion: parseFloat(actWeight),
        es_obligatorio: true,
        extensiones_permitidas: 'pdf,zip',
        tamano_max_mb: 25,
        max_reenvios: 3
      });

      const updatedActs = await api.getActivities(selectedCourse.id);
      setActivities(updatedActs);
      setShowAddActModal(false);
      setActTitle('');
      setActInstructions('');
      alert('Actividad académica creada exitosamente.');
    } catch (err) {
      setActError(err.message);
    }
  };

  const role = user?.rol?.codigo;
  const sumaPonderaciones = activities.reduce((acc, a) => acc + parseFloat(a.ponderacion || 0), 0);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1>Programas de Maestría y Cursos Preparatorios</h1>
          <p style={{ color: 'var(--text-sec)' }}>
            Estructuración curricular, actividades de nivelación y control de ponderaciones.
          </p>
        </div>

        {['ADMIN', 'COORDINADOR'].includes(role) && selectedCourse && (
          <button
            onClick={() => { setActError(null); setShowAddActModal(true); }}
            className="btn btn-primary"
          >
            <Plus size={16} />
            <span>Nueva Actividad / Proyecto</span>
          </button>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
        {/* Lista de Programas y Cursos */}
        <div className="card" style={{ padding: '20px' }}>
          <h3 style={{ marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={18} color="#1E3A8A" />
            <span>Cursos Activos</span>
          </h3>

          {loading ? (
            <p>Cargando cursos...</p>
          ) : (
            courses.map((crs) => {
              const isSelected = selectedCourse?.id === crs.id;
              return (
                <div
                  key={crs.id}
                  onClick={() => handleSelectCourse(crs)}
                  style={{
                    padding: '14px',
                    borderRadius: '12px',
                    backgroundColor: isSelected ? 'var(--color-sec)' : 'var(--surface-muted)',
                    marginBottom: '10px',
                    cursor: 'pointer',
                    border: isSelected ? '1px solid var(--color-sec-text)' : '1px solid var(--border-light)',
                    transition: 'all 0.2s'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong>{crs.codigo}</strong>
                    <Badge type={crs.estado} />
                  </div>
                  <div style={{ fontSize: '0.9rem', marginTop: '4px', color: 'var(--text-main)', fontWeight: 500 }}>
                    {crs.nombre}
                  </div>
                  <small style={{ color: 'var(--text-sec)' }}>Nota mínima de aprobación: {crs.nota_minima} pts</small>
                </div>
              );
            })
          )}
        </div>

        {/* Detalle de Actividades y Ponderación */}
        <div className="card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
            <div>
              <h3>Actividades de: {selectedCourse?.nombre || 'Seleccione un curso'}</h3>
              <small style={{ color: 'var(--text-sec)' }}>Ponderación acumulada: <strong>{sumaPonderaciones}% / 100%</strong></small>
            </div>
            <Badge
              type={sumaPonderaciones === 100 ? 'APROBADO' : 'MEDIO'}
              text={sumaPonderaciones === 100 ? 'Ponderación Completa (100%)' : `Incompleto (${sumaPonderaciones}%)`}
            />
          </div>

          {activities.length === 0 ? (
            <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-sec)' }}>
              No hay actividades registradas para este curso.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {activities.map((act) => (
                <div key={act.id} style={{
                  padding: '16px',
                  borderRadius: '14px',
                  border: '1px solid var(--border-light)',
                  background: '#FFFFFF',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  boxShadow: '0 2px 6px rgba(0,0,0,0.02)'
                }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <strong style={{ fontSize: '0.975rem' }}>{act.titulo}</strong>
                      <Badge type={act.tipo} />
                    </div>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-sec)', margin: '6px 0' }}>
                      {act.instrucciones || 'Sin instrucciones adicionales.'}
                    </p>
                    <div style={{ display: 'flex', gap: '14px', fontSize: '0.8rem', color: 'var(--text-sec)' }}>
                      <span>Fecha límite: <strong>{new Date(act.fecha_limite).toLocaleDateString()}</strong></span>
                      <span>Formatos: <code>{act.extensiones_permitidas}</code></span>
                      <span>Máx reenvíos: {act.max_reenvios}</span>
                    </div>
                  </div>

                  <div style={{ textAlign: 'right', minWidth: '90px' }}>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-primary-text)' }}>
                      {act.ponderacion}%
                    </div>
                    <small style={{ color: 'var(--text-sec)' }}>Ponderación</small>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Modal Crear Actividad */}
      <Modal
        isOpen={showAddActModal}
        onClose={() => setShowAddActModal(false)}
        title={`Nueva Actividad para: ${selectedCourse?.nombre}`}
      >
        {actError && (
          <div style={{ background: '#FEE2E2', color: '#DC2626', padding: '10px', borderRadius: '8px', marginBottom: '14px', fontSize: '0.875rem' }}>
            {actError}
          </div>
        )}
        <form onSubmit={handleCreateActivity}>
          <div className="form-group">
            <label className="form-label">Título de la Actividad o Proyecto</label>
            <input
              type="text"
              className="form-input"
              placeholder="Ej. Taller 3: Optimización Matemática..."
              value={actTitle}
              onChange={(e) => setActTitle(e.target.value)}
              required
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label className="form-label">Tipo de Actividad</label>
              <select className="form-select" value={actType} onChange={(e) => setActType(e.target.value)}>
                <option value="INDIVIDUAL">Actividad Individual</option>
                <option value="PROYECTO">Proyecto Integrador</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Ponderación (%) [Máx disponible: {100 - sumaPonderaciones}%]</label>
              <input
                type="number"
                className="form-input"
                min="1"
                max={100 - sumaPonderaciones}
                value={actWeight}
                onChange={(e) => setActWeight(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Fecha Límite de Entrega</label>
            <input
              type="datetime-local"
              className="form-input"
              value={actDeadline}
              onChange={(e) => setActDeadline(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Instrucciones</label>
            <textarea
              className="form-textarea"
              rows={3}
              placeholder="Detalle los objetivos, pautas de entrega y rúbrica..."
              value={actInstructions}
              onChange={(e) => setActInstructions(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn btn-outline" onClick={() => setShowAddActModal(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary">
              Crear Actividad
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
