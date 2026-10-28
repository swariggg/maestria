import React, { useState, useEffect } from 'react';
import { BookOpen, Plus, Layers, GraduationCap, CalendarDays, Pencil, ArrowRight } from 'lucide-react';
import { api } from '../services/api';
import Badge from '../components/Badge';
import Modal from '../components/Modal';

const FLUJO_ESTADOS = ['PLANIFICADA', 'ABIERTA', 'EN_CURSO', 'CERRADA', 'FINALIZADA'];
const ETIQUETA_ESTADO = {
  PLANIFICADA: 'Planificada',
  ABIERTA: 'Abierta',
  EN_CURSO: 'En curso',
  CERRADA: 'Cerrada',
  FINALIZADA: 'Finalizada'
};
const siguienteEstado = (estado) => FLUJO_ESTADOS[FLUJO_ESTADOS.indexOf(estado) + 1] || null;

// Las fechas llegan como 'AAAA-MM-DD'; se interpretan en hora local para no correr un día
const formatoFecha = (valor) => new Date(`${valor}T00:00:00`).toLocaleDateString('es-EC', { day: '2-digit', month: 'short', year: 'numeric' });

const CONV_VACIA = {
  codigo: '',
  nombre: '',
  fecha_apertura: '',
  fecha_cierre: '',
  fecha_inicio_preparatorio: '',
  fecha_fin_preparatorio: ''
};

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

  // Modal Crear Programa
  const [showAddProgModal, setShowAddProgModal] = useState(false);
  const [progCode, setProgCode] = useState('');
  const [progName, setProgName] = useState('');
  const [progDescription, setProgDescription] = useState('');
  const [progError, setProgError] = useState(null);
  const [progSaving, setProgSaving] = useState(false);
  const [progSuccess, setProgSuccess] = useState(null);

  // Convocatorias por programa
  const [convsByProg, setConvsByProg] = useState({});
  const [convModal, setConvModal] = useState(null); // { programa, convocatoria (null = nueva) }
  const [convForm, setConvForm] = useState(CONV_VACIA);
  const [convError, setConvError] = useState(null);
  const [convSaving, setConvSaving] = useState(false);
  const [estadoModal, setEstadoModal] = useState(null); // convocatoria a avanzar
  const [estadoError, setEstadoError] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const progs = await api.getPrograms();
      setPrograms(progs);
      if (['ADMIN', 'COORDINADOR'].includes(user?.rol?.codigo)) {
        await loadConvocatorias(progs);
      }
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

  const loadConvocatorias = async (progs) => {
    const listas = await Promise.all(progs.map((p) => api.getConvocatorias(p.id).catch(() => [])));
    const mapa = {};
    progs.forEach((p, i) => { mapa[p.id] = listas[i]; });
    setConvsByProg(mapa);
  };

  const reloadConvocatoriasDe = async (programaId) => {
    const lista = await api.getConvocatorias(programaId);
    setConvsByProg((prev) => ({ ...prev, [programaId]: lista }));
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

  const openAddProgram = () => {
    setProgCode('');
    setProgName('');
    setProgDescription('');
    setProgError(null);
    setShowAddProgModal(true);
  };

  const handleCreateProgram = async (e) => {
    e.preventDefault();
    setProgError(null);
    setProgSaving(true);
    try {
      const nuevo = await api.createProgram({
        codigo: progCode,
        nombre: progName,
        descripcion: progDescription || null
      });
      const progs = await api.getPrograms();
      setPrograms(progs);
      await loadConvocatorias(progs);
      setShowAddProgModal(false);
      setProgSuccess(`Programa ${nuevo.codigo} creado correctamente.`);
    } catch (err) {
      setProgError(err.message);
    } finally {
      setProgSaving(false);
    }
  };

  const openConvocatoria = (programa, convocatoria = null) => {
    setConvForm(convocatoria ? {
      codigo: convocatoria.codigo,
      nombre: convocatoria.nombre,
      fecha_apertura: convocatoria.fecha_apertura,
      fecha_cierre: convocatoria.fecha_cierre,
      fecha_inicio_preparatorio: convocatoria.fecha_inicio_preparatorio,
      fecha_fin_preparatorio: convocatoria.fecha_fin_preparatorio
    } : CONV_VACIA);
    setConvError(null);
    setConvModal({ programa, convocatoria });
  };

  const setConvField = (campo) => (e) => {
    const valor = campo === 'codigo' ? e.target.value.toUpperCase() : e.target.value;
    setConvForm((prev) => ({ ...prev, [campo]: valor }));
  };

  const handleSaveConvocatoria = async (e) => {
    e.preventDefault();
    setConvError(null);

    if (convForm.fecha_cierre < convForm.fecha_apertura) {
      setConvError('La fecha de cierre no puede ser anterior a la fecha de apertura.');
      return;
    }
    if (convForm.fecha_fin_preparatorio < convForm.fecha_inicio_preparatorio) {
      setConvError('El fin del preparatorio no puede ser anterior al inicio.');
      return;
    }

    const { programa, convocatoria } = convModal;
    const { codigo, ...datos } = convForm;
    setConvSaving(true);
    try {
      if (convocatoria) {
        await api.updateConvocatoria(convocatoria.id, datos);
        setProgSuccess(`Convocatoria ${convocatoria.codigo} actualizada.`);
      } else {
        const nueva = await api.createConvocatoria({ programa_id: programa.id, codigo, ...datos });
        setProgSuccess(`Convocatoria ${nueva.codigo} creada como Planificada. Ábrala cuando esté lista para recibir postulantes.`);
      }
      await reloadConvocatoriasDe(programa.id);
      setConvModal(null);
    } catch (err) {
      setConvError(err.message);
    } finally {
      setConvSaving(false);
    }
  };

  const handleAdvanceEstado = async () => {
    setEstadoError(null);
    const siguiente = siguienteEstado(estadoModal.estado);
    try {
      await api.changeConvocatoriaEstado(estadoModal.id, siguiente);
      await reloadConvocatoriasDe(estadoModal.programa_id);
      setProgSuccess(`Convocatoria ${estadoModal.codigo} ahora está ${ETIQUETA_ESTADO[siguiente].toLowerCase()}.`);
      setEstadoModal(null);
    } catch (err) {
      setEstadoError(err.message);
    }
  };

  const role = user?.rol?.codigo;
  const canManage = ['ADMIN', 'COORDINADOR'].includes(role);
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

        {canManage && (
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button onClick={openAddProgram} className="btn btn-primary">
              <Plus size={16} />
              <span>Nuevo Programa</span>
            </button>
            {selectedCourse && (
              <button
                onClick={() => { setActError(null); setShowAddActModal(true); }}
                className="btn btn-secondary"
              >
                <Plus size={16} />
                <span>Nueva Actividad / Proyecto</span>
              </button>
            )}
          </div>
        )}
      </div>

      {progSuccess && (
        <div style={{
          background: 'var(--status-success-bg)',
          color: 'var(--status-success-text)',
          padding: '12px 18px',
          borderRadius: '16px',
          marginBottom: '20px',
          fontWeight: 500
        }}>
          {progSuccess}
        </div>
      )}

      {/* Programas de Maestría */}
      <h3 style={{ marginBottom: '12px' }}>Programas de Maestría</h3>
      {!loading && programs.length === 0 ? (
        <div className="card" style={{ marginBottom: '28px' }}>
          <p style={{ color: 'var(--text-sec)' }}>
            {canManage ? 'Aún no hay programas. Cree el primero con "Nuevo Programa".' : 'No hay programas disponibles.'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: canManage ? '1fr' : 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px', marginBottom: '28px' }}>
          {programs.map((prog) => {
            const convocatorias = convsByProg[prog.id] || [];
            return (
              <div key={prog.id} className="card">
                <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                  <div className="kpi-icon duo">
                    <GraduationCap size={22} />
                  </div>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap', marginBottom: '6px' }}>
                      <Badge type="PENDIENTE" text={prog.codigo} />
                      <Badge type={prog.estado} />
                    </div>
                    <h3 style={{ fontSize: '1rem', lineHeight: 1.35 }}>{prog.nombre}</h3>
                    {prog.descripcion && (
                      <small style={{ display: 'block', marginTop: '4px' }}>{prog.descripcion}</small>
                    )}
                  </div>
                  {canManage && (
                    <button onClick={() => openConvocatoria(prog)} className="btn btn-secondary" style={{ padding: '8px 14px', fontSize: '0.825rem' }}>
                      <Plus size={14} />
                      <span>Nueva convocatoria</span>
                    </button>
                  )}
                </div>

                {canManage && (
                  <div style={{ marginTop: '16px', borderTop: '1px solid var(--border-light)', paddingTop: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px', fontWeight: 600, fontSize: '0.875rem', color: 'var(--color-navy)' }}>
                      <CalendarDays size={16} />
                      <span>Convocatorias ({convocatorias.length})</span>
                    </div>

                    {convocatorias.length === 0 ? (
                      <small>Este programa aún no tiene convocatorias.</small>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {convocatorias.map((conv) => {
                          const siguiente = siguienteEstado(conv.estado);
                          return (
                            <div key={conv.id} style={{
                              padding: '12px 14px',
                              borderRadius: '14px',
                              background: 'var(--surface-muted)',
                              border: '1px solid var(--border-light)',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              gap: '12px',
                              flexWrap: 'wrap'
                            }}>
                              <div style={{ minWidth: 0 }}>
                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                                  <strong style={{ fontSize: '0.925rem' }}>{conv.codigo}</strong>
                                  <span style={{ fontSize: '0.9rem' }}>{conv.nombre}</span>
                                  <Badge type={conv.estado} text={ETIQUETA_ESTADO[conv.estado] || conv.estado} />
                                </div>
                                <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', fontSize: '0.8rem', color: 'var(--text-sec)', marginTop: '4px' }}>
                                  <span>Inscripciones: <strong>{formatoFecha(conv.fecha_apertura)} – {formatoFecha(conv.fecha_cierre)}</strong></span>
                                  <span>Preparatorio: <strong>{formatoFecha(conv.fecha_inicio_preparatorio)} – {formatoFecha(conv.fecha_fin_preparatorio)}</strong></span>
                                </div>
                              </div>
                              <div style={{ display: 'flex', gap: '8px' }}>
                                {conv.estado !== 'FINALIZADA' && (
                                  <button onClick={() => openConvocatoria(prog, conv)} className="btn btn-outline" style={{ padding: '7px 12px', fontSize: '0.8rem' }}>
                                    <Pencil size={13} />
                                    <span>Editar</span>
                                  </button>
                                )}
                                {siguiente && (
                                  <button onClick={() => { setEstadoError(null); setEstadoModal(conv); }} className="btn btn-primary" style={{ padding: '7px 12px', fontSize: '0.8rem' }}>
                                    <ArrowRight size={13} />
                                    <span>Cambiar estado</span>
                                  </button>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
        {/* Lista de Programas y Cursos */}
        <div className="card" style={{ padding: '20px' }}>
          <h3 style={{ marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={18} color="var(--color-navy)" />
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
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-navy)' }}>
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

      {/* Modal Crear Programa */}
      <Modal
        isOpen={showAddProgModal}
        onClose={() => setShowAddProgModal(false)}
        title="Nuevo Programa de Maestría"
      >
        {progError && (
          <div style={{ background: 'var(--status-danger-bg)', color: 'var(--status-danger-text)', padding: '10px 14px', borderRadius: '12px', marginBottom: '14px', fontSize: '0.875rem' }}>
            {progError}
          </div>
        )}
        <form onSubmit={handleCreateProgram}>
          <div className="form-group">
            <label className="form-label">Código del Programa</label>
            <input
              type="text"
              className="form-input"
              placeholder="Ej. MDS-01"
              value={progCode}
              onChange={(e) => setProgCode(e.target.value.toUpperCase())}
              minLength={2}
              maxLength={50}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Nombre del Programa</label>
            <input
              type="text"
              className="form-input"
              placeholder="Ej. Maestría en Ciencia de Datos"
              value={progName}
              onChange={(e) => setProgName(e.target.value)}
              minLength={3}
              maxLength={250}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Descripción</label>
            <textarea
              className="form-textarea"
              rows={3}
              placeholder="Enfoque, perfil de egreso y líneas de investigación..."
              value={progDescription}
              onChange={(e) => setProgDescription(e.target.value)}
            />
          </div>

          {role === 'COORDINADOR' && (
            <small style={{ display: 'block', marginBottom: '8px' }}>
              Quedará asignado como coordinador de este programa.
            </small>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn btn-outline" onClick={() => setShowAddProgModal(false)}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={progSaving}>
              {progSaving ? 'Guardando...' : 'Crear Programa'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Crear / Editar Convocatoria */}
      <Modal
        isOpen={!!convModal}
        onClose={() => setConvModal(null)}
        title={convModal?.convocatoria ? `Editar convocatoria ${convModal.convocatoria.codigo}` : 'Nueva Convocatoria'}
      >
        {convModal && (
          <small style={{ display: 'block', marginBottom: '14px' }}>
            Programa: <strong>{convModal.programa.nombre}</strong>
          </small>
        )}
        {convError && (
          <div style={{ background: 'var(--status-danger-bg)', color: 'var(--status-danger-text)', padding: '10px 14px', borderRadius: '12px', marginBottom: '14px', fontSize: '0.875rem' }}>
            {convError}
          </div>
        )}
        <form onSubmit={handleSaveConvocatoria}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '12px' }}>
            <div className="form-group">
              <label className="form-label">Código</label>
              <input
                type="text"
                className="form-input"
                placeholder="Ej. 2027-I"
                value={convForm.codigo}
                onChange={setConvField('codigo')}
                disabled={!!convModal?.convocatoria}
                minLength={2}
                maxLength={50}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Nombre</label>
              <input
                type="text"
                className="form-input"
                placeholder="Ej. Convocatoria Primer Semestre 2027"
                value={convForm.nombre}
                onChange={setConvField('nombre')}
                minLength={3}
                maxLength={200}
                required
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label className="form-label">Apertura de inscripciones</label>
              <input type="date" className="form-input" value={convForm.fecha_apertura} onChange={setConvField('fecha_apertura')} required />
            </div>
            <div className="form-group">
              <label className="form-label">Cierre de inscripciones</label>
              <input type="date" className="form-input" value={convForm.fecha_cierre} min={convForm.fecha_apertura} onChange={setConvField('fecha_cierre')} required />
            </div>
            <div className="form-group">
              <label className="form-label">Inicio del preparatorio</label>
              <input type="date" className="form-input" value={convForm.fecha_inicio_preparatorio} onChange={setConvField('fecha_inicio_preparatorio')} required />
            </div>
            <div className="form-group">
              <label className="form-label">Fin del preparatorio</label>
              <input type="date" className="form-input" value={convForm.fecha_fin_preparatorio} min={convForm.fecha_inicio_preparatorio} onChange={setConvField('fecha_fin_preparatorio')} required />
            </div>
          </div>

          {!convModal?.convocatoria && (
            <small style={{ display: 'block', marginBottom: '8px' }}>
              La convocatoria se crea como Planificada. Los postulantes podrán inscribirse cuando la cambie a Abierta.
            </small>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn btn-outline" onClick={() => setConvModal(null)}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={convSaving}>
              {convSaving ? 'Guardando...' : (convModal?.convocatoria ? 'Guardar cambios' : 'Crear Convocatoria')}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal Cambiar Estado de Convocatoria */}
      <Modal
        isOpen={!!estadoModal}
        onClose={() => setEstadoModal(null)}
        title="Cambiar estado de la convocatoria"
      >
        {estadoModal && (
          <div>
            {estadoError && (
              <div style={{ background: 'var(--status-danger-bg)', color: 'var(--status-danger-text)', padding: '10px 14px', borderRadius: '12px', marginBottom: '14px', fontSize: '0.875rem' }}>
                {estadoError}
              </div>
            )}
            <p style={{ marginBottom: '16px' }}>
              <strong>{estadoModal.codigo}</strong> · {estadoModal.nombre}
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', justifyContent: 'center', padding: '16px', borderRadius: '16px', background: 'var(--surface-muted)', marginBottom: '14px' }}>
              <Badge type={estadoModal.estado} text={ETIQUETA_ESTADO[estadoModal.estado]} />
              <ArrowRight size={18} color="var(--color-wine)" />
              <Badge type={siguienteEstado(estadoModal.estado)} text={ETIQUETA_ESTADO[siguienteEstado(estadoModal.estado)]} />
            </div>
            <small style={{ display: 'block' }}>
              Las convocatorias solo avanzan: Planificada, Abierta, En curso, Cerrada y Finalizada. Este cambio no se puede deshacer.
            </small>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
              <button type="button" className="btn btn-outline" onClick={() => setEstadoModal(null)}>
                Cancelar
              </button>
              <button type="button" className="btn btn-primary" onClick={handleAdvanceEstado}>
                Confirmar cambio
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Modal Crear Actividad */}
      <Modal
        isOpen={showAddActModal}
        onClose={() => setShowAddActModal(false)}
        title={`Nueva Actividad para: ${selectedCourse?.nombre}`}
      >
        {actError && (
          <div style={{ background: 'var(--status-danger-bg)', color: 'var(--status-danger-text)', padding: '10px', borderRadius: '8px', marginBottom: '14px', fontSize: '0.875rem' }}>
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
