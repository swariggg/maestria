import React, { useState, useEffect } from 'react';
import { BookOpen, Plus, Layers, GraduationCap, CalendarDays, Pencil, ArrowRight, Trash2, FileText, ListChecks, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import Badge from '../components/Badge';
import CourseBanner from '../components/visual/CourseBanner';
import CourseTile from '../components/visual/CourseTile';
import Modal from '../components/Modal';
import RequirementsManager from '../components/RequirementsManager';
import { RubricEditor, MaterialsPanel } from '../components/CourseExtras';
import TutorCard from '../components/TutorCard';

const FLUJO_ESTADOS = ['PLANIFICADA', 'ABIERTA', 'EN_CURSO', 'CERRADA', 'FINALIZADA'];
const ETIQUETA_ESTADO = {
  PLANIFICADA: 'Planificada',
  ABIERTA: 'Abierta',
  EN_CURSO: 'En curso',
  CERRADA: 'Cerrada',
  FINALIZADA: 'Finalizada'
};
// Cambios permitidos (los mismos que valida el backend). Reabrir exige motivo.
const TRANSICIONES = {
  PLANIFICADA: ['ABIERTA'],
  ABIERTA: ['EN_CURSO'],
  EN_CURSO: ['CERRADA', 'ABIERTA'],
  CERRADA: ['FINALIZADA'],
  FINALIZADA: ['CERRADA'],
};
const siguienteEstado = (estado) => (TRANSICIONES[estado] || [])[0] || null;
const MODALIDADES = { EN_LINEA: 'En línea', PRESENCIAL: 'Presencial', HIBRIDA: 'Híbrida' };
const hoyISO = () => {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
};

// Las fechas llegan como 'AAAA-MM-DD'; se interpretan en hora local para no correr un día
const formatoFecha = (valor) => new Date(`${valor}T00:00:00`).toLocaleDateString('es-EC', { day: '2-digit', month: 'short', year: 'numeric' });

const CONV_VACIA = {
  codigo: '',
  nombre: '',
  fecha_apertura: '',
  fecha_cierre: '',
  fecha_inicio_preparatorio: '',
  fecha_fin_preparatorio: '',
  cupo_maximo: 60,
  modalidad: 'EN_LINEA'
};

const CONV_PERMITE_CURSOS = ['PLANIFICADA', 'ABIERTA', 'EN_CURSO'];

// Fecha local 'AAAA-MM-DDTHH:MM' para inputs datetime-local, y de vuelta sin zona horaria
const aInputFecha = (valor) => (valor ? String(valor).slice(0, 16) : '');
const desdeInputFecha = (valor) => (valor.length === 16 ? `${valor}:00` : valor);
const ahoraInput = () => {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
};

const CURSO_VACIO = { codigo: '', nombre: '', descripcion: '', nota_minima: 70, ponderacion_total: 30, tutor_id: '', motivo_tutor: '' };
const TIPOS_ACTIVIDAD = [
  { valor: 'ASIGNACION', texto: 'Asignación' },
  { valor: 'PRUEBA', texto: 'Prueba o evaluación' },
  { valor: 'PROYECTO', texto: 'Proyecto' },
];
const PUNTOS_POR_DEFECTO = { ASIGNACION: 4, PRUEBA: 6 };
const actividadVacia = () => ({
  titulo: '',
  tipo: 'ASIGNACION',
  instrucciones: '',
  fecha_apertura: ahoraInput(),
  fecha_limite: '',
  ponderacion: 4,
  es_obligatorio: true,
  extensiones_permitidas: 'pdf,zip',
  tamano_max_mb: 25,
  max_reenvios: 3
});

export default function CoursesPage({ user }) {
  const [programs, setPrograms] = useState([]);
  const [selectedProg, setSelectedProg] = useState(null);
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  // Modal Crear / Editar Actividad
  const [actModal, setActModal] = useState(null); // { actividad: null (nueva) | objeto }
  const [actForm, setActForm] = useState(actividadVacia());
  const [actError, setActError] = useState(null);
  const [plantillas, setPlantillas] = useState([]);
  const [puntosEstandar, setPuntosEstandar] = useState(PUNTOS_POR_DEFECTO);
  const [tplModal, setTplModal] = useState(false);
  const [tplForm, setTplForm] = useState({ titulo: '', tipo: 'ASIGNACION', ponderacion: 4, extensiones_permitidas: 'pdf,docx', instrucciones: '' });
  const [tplError, setTplError] = useState(null);

  // Modal Crear / Editar Curso y Requisitos
  const [courseModal, setCourseModal] = useState(null); // { convocatoria, curso: null | objeto }
  const [courseForm, setCourseForm] = useState(CURSO_VACIO);
  const [courseError, setCourseError] = useState(null);
  const [courseTutors, setCourseTutors] = useState([]);
  const [reqConv, setReqConv] = useState(null);

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
  const [estadoDestino, setEstadoDestino] = useState('');
  const [estadoMotivo, setEstadoMotivo] = useState('');
  const [rubricAct, setRubricAct] = useState(null);

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

  const reloadCourses = async (seleccionarId) => {
    const crs = await api.getCourses();
    setCourses(crs);
    const elegido = crs.find((c) => c.id === (seleccionarId ?? selectedCourse?.id)) || crs[0] || null;
    setSelectedCourse(elegido);
    setActivities(elegido ? await api.getActivities(elegido.id) : []);
  };

  const cargarPlantillas = async (programaId) => {
    if (!programaId) return;
    try {
      const data = await api.getTemplates(programaId);
      setPlantillas(data.plantillas);
      setPuntosEstandar({ ...PUNTOS_POR_DEFECTO, ...data.puntos_estandar });
    } catch (err) {
      setPlantillas([]);
    }
  };

  const usarPlantilla = (id) => {
    const p = plantillas.find((x) => x.id === parseInt(id));
    if (!p) return;
    setActForm((prev) => ({
      ...prev,
      titulo: p.titulo, tipo: p.tipo, instrucciones: p.instrucciones || '', ponderacion: p.ponderacion,
      es_obligatorio: p.es_obligatorio, extensiones_permitidas: p.extensiones_permitidas,
      tamano_max_mb: p.tamano_max_mb, max_reenvios: p.max_reenvios
    }));
  };

  const openActivity = (actividad = null) => {
    setActError(null);
    cargarPlantillas(selectedCourse?.programa_id);
    setActForm(actividad ? {
      titulo: actividad.titulo,
      tipo: actividad.tipo === 'INDIVIDUAL' ? 'ASIGNACION' : actividad.tipo,
      instrucciones: actividad.instrucciones || '',
      fecha_apertura: aInputFecha(actividad.fecha_apertura),
      fecha_limite: aInputFecha(actividad.fecha_limite),
      ponderacion: actividad.ponderacion,
      es_obligatorio: actividad.es_obligatorio,
      extensiones_permitidas: actividad.extensiones_permitidas,
      tamano_max_mb: actividad.tamano_max_mb,
      max_reenvios: actividad.max_reenvios
    } : actividadVacia());
    setActModal({ actividad });
  };

  const setActField = (campo) => (e) => {
    const valor = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setActForm((prev) => {
      const nuevo = { ...prev, [campo]: valor };
      // Al cambiar el tipo, se proponen los puntos estándar (asignación 4, prueba 6)
      if (campo === 'tipo' && puntosEstandar[valor]) nuevo.ponderacion = puntosEstandar[valor];
      return nuevo;
    });
  };

  const openTemplates = () => {
    setTplError(null);
    setTplForm({ titulo: '', tipo: 'ASIGNACION', ponderacion: puntosEstandar.ASIGNACION, extensiones_permitidas: 'pdf,docx', instrucciones: '' });
    cargarPlantillas(selectedCourse?.programa_id);
    setTplModal(true);
  };

  const handleSaveTemplate = async (e) => {
    e.preventDefault();
    setTplError(null);
    try {
      await api.createTemplate({ ...tplForm, programa_id: selectedCourse.programa_id, ponderacion: parseFloat(tplForm.ponderacion),
        instrucciones: tplForm.instrucciones || null });
      setTplForm({ titulo: '', tipo: 'ASIGNACION', ponderacion: puntosEstandar.ASIGNACION, extensiones_permitidas: 'pdf,docx', instrucciones: '' });
      cargarPlantillas(selectedCourse.programa_id);
    } catch (err) {
      setTplError(err.message);
    }
  };

  const handleDeleteTemplate = async (id) => {
    try {
      await api.deleteTemplate(id);
      cargarPlantillas(selectedCourse.programa_id);
    } catch (err) {
      setTplError(err.message);
    }
  };

  const handleSaveActivity = async (e) => {
    e.preventDefault();
    setActError(null);
    const editando = actModal.actividad;
    const otras = activities.filter((a) => a.estado === 'ACTIVO' && a.id !== editando?.id);
    const suma = otras.reduce((acc, a) => acc + parseFloat(a.ponderacion || 0), 0) + parseFloat(actForm.ponderacion);
    if (suma > totalCurso) {
      setActError(`Las actividades sumarían ${suma} puntos y el curso vale ${totalCurso}.`);
      return;
    }
    if (actForm.fecha_limite <= actForm.fecha_apertura) {
      setActError('La fecha límite debe ser posterior a la fecha de apertura.');
      return;
    }
    const datos = {
      ...actForm,
      instrucciones: actForm.instrucciones || null,
      fecha_apertura: desdeInputFecha(actForm.fecha_apertura),
      fecha_limite: desdeInputFecha(actForm.fecha_limite),
      ponderacion: parseFloat(actForm.ponderacion),
      tamano_max_mb: parseInt(actForm.tamano_max_mb, 10),
      max_reenvios: parseInt(actForm.max_reenvios, 10)
    };
    try {
      if (editando) {
        await api.updateActivity(editando.id, datos);
        setProgSuccess(`Actividad "${datos.titulo}" actualizada.`);
      } else {
        await api.createActivity({ curso_id: selectedCourse.id, ...datos });
        setProgSuccess(`Actividad "${datos.titulo}" creada.`);
      }
      setActivities(await api.getActivities(selectedCourse.id));
      setActModal(null);
    } catch (err) {
      setActError(err.message);
    }
  };

  const handleDeleteActivity = async (act) => {
    if (!window.confirm(`¿Eliminar la actividad "${act.titulo}"? Si ya tiene entregas, se dará de baja y se conservarán sus evidencias.`)) return;
    try {
      const res = await api.deleteActivity(act.id);
      setProgSuccess(res.mensaje);
      setActivities(await api.getActivities(selectedCourse.id));
    } catch (err) {
      setProgSuccess(null);
      alert(err.message);
    }
  };

  const openCourse = async (convocatoria, curso = null) => {
    setCourseError(null);
    setCourseForm(curso ? {
      codigo: curso.codigo,
      nombre: curso.nombre,
      descripcion: curso.descripcion || '',
      nota_minima: curso.nota_minima,
      ponderacion_total: curso.ponderacion_total,
      tutor_id: curso.tutor_id || '',
      motivo_tutor: ''
    } : CURSO_VACIO);
    setCourseModal({ convocatoria, curso });
    try {
      // Solo los tutores que trabajan en el programa de la convocatoria
      setCourseTutors(await api.getTutors(convocatoria?.programa_id));
    } catch (err) {
      setCourseTutors([]);
    }
  };

  const setCourseField = (campo) => (e) => {
    const valor = campo === 'codigo' ? e.target.value.toUpperCase() : e.target.value;
    setCourseForm((prev) => ({ ...prev, [campo]: valor }));
  };

  const handleSaveCourse = async (e) => {
    e.preventDefault();
    setCourseError(null);
    const tutorId = courseForm.tutor_id ? parseInt(courseForm.tutor_id) : null;
    const datos = {
      codigo: courseForm.codigo,
      nombre: courseForm.nombre,
      descripcion: courseForm.descripcion || null,
      nota_minima: parseFloat(courseForm.nota_minima),
      ponderacion_total: parseFloat(courseForm.ponderacion_total)
    };
    try {
      let guardado;
      if (courseModal.curso) {
        guardado = await api.updateCourse(courseModal.curso.id, datos);
        if (tutorId && tutorId !== courseModal.curso.tutor_id) {
          guardado = await api.setCourseTutor(courseModal.curso.id, { tutor_id: tutorId, motivo: courseForm.motivo_tutor || null });
        }
        setProgSuccess(`Curso ${guardado.codigo} actualizado.`);
      } else {
        guardado = await api.createCourse({ convocatoria_id: courseModal.convocatoria.id, ...datos, tutor_id: tutorId });
        setProgSuccess(`Curso ${guardado.codigo} creado y asignado a los inscritos de ${courseModal.convocatoria.codigo}.`);
      }
      await reloadCourses(guardado.id);
      setCourseModal(null);
    } catch (err) {
      setCourseError(err.message);
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
      fecha_fin_preparatorio: convocatoria.fecha_fin_preparatorio,
      cupo_maximo: convocatoria.cupo_maximo ?? 60,
      modalidad: convocatoria.modalidad || 'EN_LINEA'
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
    const { codigo, ...resto } = convForm;
    const datos = { ...resto, cupo_maximo: parseInt(resto.cupo_maximo, 10) || 60 };
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
    const siguiente = estadoDestino;
    try {
      await api.changeConvocatoriaEstado(estadoModal.id, siguiente, estadoMotivo || null);
      await reloadConvocatoriasDe(estadoModal.programa_id);
      setProgSuccess(`Convocatoria ${estadoModal.codigo} ahora está ${ETIQUETA_ESTADO[siguiente].toLowerCase()}.`);
      setEstadoModal(null);
    } catch (err) {
      setEstadoError(err.message);
    }
  };

  const role = user?.rol?.codigo;
  const canManage = ['ADMIN', 'COORDINADOR'].includes(role);
  const esPostulante = role === 'POSTULANTE';
  const miMaestria = esPostulante ? programs[0] : null;
  const sumaPonderaciones = activities
    .filter((a) => a.estado === 'ACTIVO')
    .reduce((acc, a) => acc + parseFloat(a.ponderacion || 0), 0);
  const todasConvocatorias = Object.values(convsByProg).flat();
  const convDeCurso = (curso) => todasConvocatorias.find((c) => c.id === curso?.convocatoria_id);
  const esTutorDelCurso = role === 'TUTOR' && !!selectedCourse && selectedCourse.tutor_id === user?.id;
  const cursoEditable = (canManage && CONV_PERMITE_CURSOS.includes(convDeCurso(selectedCourse)?.estado)) || esTutorDelCurso;
  const totalCurso = parseFloat(selectedCourse?.ponderacion_total || 100);

  const irAlCurso = (crs) => {
    handleSelectCourse(crs);
    requestAnimationFrame(() => document.querySelector('.course-banner')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  };

  return (
    <div>
      {/* Al entrar a un curso: franja con su nombre bajo la navegación (postulante y tutor) */}
      {!canManage && selectedCourse && <CourseBanner curso={selectedCourse} convocatoria={convDeCurso(selectedCourse)} />}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1>{esPostulante ? 'Mis cursos preparatorios' : 'Programas de Maestría y Cursos Preparatorios'}</h1>
          <p style={{ color: 'var(--text-sec)' }}>
            {esPostulante
              ? (miMaestria ? <>Maestría: <strong style={{ color: 'var(--color-uide)' }}>{miMaestria.nombre}</strong>. Entre a un curso para ver sus actividades.</> : 'Aún no está inscrito en una maestría.')
              : 'Estructuración curricular, actividades de nivelación y control de ponderaciones.'}
          </p>
        </div>

        {(canManage || esTutorDelCurso) && (
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {canManage && (
              <button onClick={openAddProgram} className="btn btn-primary">
                <Plus size={16} />
                <span>Nuevo Programa</span>
              </button>
            )}
            {canManage && selectedCourse && (
              <button onClick={openTemplates} className="btn btn-outline">
                <ListChecks size={16} />
                <span>Plantillas del programa</span>
              </button>
            )}
            {selectedCourse && cursoEditable && (
              <button
                onClick={() => openActivity(null)}
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
      {!esPostulante && (<>
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
                                  <span>Inscritos: <strong>{conv.inscritos ?? 0} / {conv.cupo_maximo ?? 60}</strong></span>
                                  <span>{MODALIDADES[conv.modalidad] || conv.modalidad}</span>
                                </div>
                                {['EN_CURSO', 'CERRADA'].includes(conv.estado) && conv.fecha_fin_preparatorio < hoyISO() && (
                                  <div className="notice-warning" style={{ marginTop: '8px', fontSize: '0.8rem' }}>
                                    <AlertCircle size={14} />
                                    <span>
                                      El preparatorio terminó el {formatoFecha(conv.fecha_fin_preparatorio)}.
                                      {conv.estado === 'EN_CURSO' ? ' Ciérrela y luego finalícela' : ' Finalícela'} para dar el resultado a los postulantes.
                                    </span>
                                  </div>
                                )}
                              </div>
                              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                <button onClick={() => setReqConv(conv)} className="btn btn-outline" style={{ padding: '7px 12px', fontSize: '0.8rem' }}>
                                  <FileText size={13} />
                                  <span>Requisitos</span>
                                </button>
                                {CONV_PERMITE_CURSOS.includes(conv.estado) && (
                                  <button onClick={() => openCourse(conv)} className="btn btn-outline" style={{ padding: '7px 12px', fontSize: '0.8rem' }}>
                                    <Plus size={13} />
                                    <span>Nuevo curso</span>
                                  </button>
                                )}
                                {conv.estado !== 'FINALIZADA' && (
                                  <button onClick={() => openConvocatoria(prog, conv)} className="btn btn-outline" style={{ padding: '7px 12px', fontSize: '0.8rem' }}>
                                    <Pencil size={13} />
                                    <span>Editar</span>
                                  </button>
                                )}
                                {siguiente && (
                                  <button onClick={() => { setEstadoError(null); setEstadoDestino(siguiente); setEstadoMotivo(''); setEstadoModal(conv); }} className="btn btn-primary" style={{ padding: '7px 12px', fontSize: '0.8rem' }}>
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
      </>)}

      <div className="courses-stack">
        {/* Cursos como tarjetas con figuras de fondo */}
        <section>
          <h3 style={{ marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={18} color="var(--color-navy)" />
            <span>{canManage ? 'Cursos Activos' : esPostulante ? 'Cursos para entrar' : 'Mis cursos'}</span>
          </h3>

          {loading ? (
            <p>Cargando cursos...</p>
          ) : courses.length === 0 ? (
            <div className="card"><small>{canManage ? 'Aún no hay cursos. Use "Nuevo curso" en una convocatoria.' : 'No tiene cursos asignados.'}</small></div>
          ) : (
            <div className="course-tiles">
              {courses.map((crs) => (
                <CourseTile
                  key={crs.id}
                  curso={crs}
                  selected={selectedCourse?.id === crs.id}
                  onClick={() => irAlCurso(crs)}
                  extra={
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {convDeCurso(crs) && <small style={{ color: 'var(--text-sec)' }}>{convDeCurso(crs).codigo}</small>}
                      <Badge type={crs.estado} />
                      {canManage && CONV_PERMITE_CURSOS.includes(convDeCurso(crs)?.estado) && (
                        <button
                          className="btn btn-outline"
                          style={{ padding: '4px 6px', border: 'none' }}
                          title="Editar curso"
                          onClick={(e) => { e.stopPropagation(); openCourse(convDeCurso(crs), crs); }}
                        >
                          <Pencil size={13} />
                        </button>
                      )}
                    </div>
                  }
                >
                  <small style={{ display: 'block', color: crs.tutor_nombre ? 'var(--text-sec)' : 'var(--status-warning-text)' }}>
                    Tutor: {crs.tutor_nombre || 'sin asignar'}
                  </small>
                  <small style={{ color: 'var(--text-sec)' }}>Vale {crs.ponderacion_total} puntos · aprueba con {crs.nota_minima}/100</small>
                </CourseTile>
              ))}
            </div>
          )}
        </section>

        {canManage && selectedCourse && <CourseBanner curso={selectedCourse} convocatoria={convDeCurso(selectedCourse)} />}

        {/* Detalle de Actividades y Ponderación */}
        <div className="card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
            <div>
              <h3>Actividades de: {selectedCourse?.nombre || 'Seleccione un curso'}</h3>
              <small style={{ color: 'var(--text-sec)' }}>Puntos asignados: <strong>{sumaPonderaciones} / {totalCurso}</strong></small>
            </div>
            {selectedCourse && (
              <Badge
                type={sumaPonderaciones === totalCurso ? 'APROBADO' : 'MEDIO'}
                text={sumaPonderaciones === totalCurso ? `Completo (${totalCurso} puntos)` : `Faltan ${totalCurso - sumaPonderaciones} puntos`}
              />
            )}
          </div>

          {activities.length === 0 ? (
            <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-sec)' }}>
              No hay actividades registradas para este curso.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {activities.map((act) => (
                <div key={act.id} style={{
                  opacity: act.estado === 'ACTIVO' ? 1 : 0.6,
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
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                      <strong style={{ fontSize: '0.975rem' }}>{act.titulo}</strong>
                      <Badge type={act.tipo} />
                      {!act.es_obligatorio && <Badge type="BAJO" text="Opcional" />}
                      {act.estado !== 'ACTIVO' && <Badge type="RECHAZADO" text="Dada de baja" />}
                    </div>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-sec)', margin: '6px 0' }}>
                      {act.instrucciones || 'Sin instrucciones adicionales.'}
                    </p>
                    <div style={{ display: 'flex', gap: '14px', fontSize: '0.8rem', color: 'var(--text-sec)' }}>
                      <span>Fecha límite: <strong>{new Date(act.fecha_limite).toLocaleDateString()}</strong></span>
                      <span>Formatos: <code>{act.extensiones_permitidas}</code></span>
                      <span>Máx intentos: {act.max_reenvios}</span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ textAlign: 'right', minWidth: '90px' }}>
                      <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-navy)' }}>
                        {act.ponderacion}
                      </div>
                      <small style={{ color: 'var(--text-sec)' }}>puntos</small>
                    </div>
                    {(canManage || role === 'TUTOR') && act.estado === 'ACTIVO' && (
                      <button className="btn btn-outline" style={{ padding: '6px 8px' }} title="Rúbrica de evaluación" onClick={() => setRubricAct(act)}>
                        <ListChecks size={14} />
                      </button>
                    )}
                    {cursoEditable && act.estado === 'ACTIVO' && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <button className="btn btn-outline" style={{ padding: '6px 8px' }} title="Editar actividad" onClick={() => openActivity(act)}>
                          <Pencil size={14} />
                        </button>
                        <button className="btn btn-outline" style={{ padding: '6px 8px' }} title="Eliminar actividad" onClick={() => handleDeleteActivity(act)}>
                          <Trash2 size={14} />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {selectedCourse && <TutorCard cursoId={selectedCourse.id} />}

      {selectedCourse && (
        <MaterialsPanel curso={selectedCourse} />
      )}

      <Modal isOpen={!!rubricAct} onClose={() => setRubricAct(null)} title={`Rúbrica: ${rubricAct?.titulo || ''}`} wide>
        {rubricAct && <RubricEditor actividad={rubricAct} onClose={() => setRubricAct(null)} />}
      </Modal>

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

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label className="form-label">Cupo máximo</label>
              <input type="number" min="1" max="2000" className="form-input" value={convForm.cupo_maximo} onChange={setConvField('cupo_maximo')} required />
            </div>
            <div className="form-group">
              <label className="form-label">Modalidad</label>
              <select className="form-select" value={convForm.modalidad} onChange={setConvField('modalidad')}>
                {Object.entries(MODALIDADES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
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
            {(TRANSICIONES[estadoModal.estado] || []).length > 1 && (
              <div className="form-group">
                <label className="form-label">Nuevo estado</label>
                <select className="form-select" value={estadoDestino} onChange={(e) => setEstadoDestino(e.target.value)}>
                  {TRANSICIONES[estadoModal.estado].map((e) => (
                    <option key={e} value={e}>{ETIQUETA_ESTADO[e]}{e === 'ABIERTA' ? ' (reabrir inscripciones)' : ''}</option>
                  ))}
                </select>
              </div>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', justifyContent: 'center', padding: '16px', borderRadius: '16px', background: 'var(--surface-muted)', marginBottom: '14px' }}>
              <Badge type={estadoModal.estado} text={ETIQUETA_ESTADO[estadoModal.estado]} />
              <ArrowRight size={18} color="var(--color-wine)" />
              <Badge type={estadoDestino} text={ETIQUETA_ESTADO[estadoDestino]} />
            </div>
            {estadoModal.estado === 'FINALIZADA' && (
              <div className="form-group">
                <label className="form-label">Motivo de la reapertura *</label>
                <input className="form-input" value={estadoMotivo} onChange={(e) => setEstadoMotivo(e.target.value)} minLength={5} required
                  placeholder="Ej.: corrección de una calificación" />
                <small style={{ display: 'block', marginTop: '4px' }}>
                  Los postulantes vuelven al estado que tenían antes del cierre y se pueden corregir notas.
                </small>
              </div>
            )}
            {estadoModal.estado === 'EN_CURSO' && estadoDestino === 'ABIERTA' && (
              <small style={{ display: 'block' }}>Solo se puede reabrir si la fecha de cierre de inscripciones todavía no pasó.</small>
            )}
            {estadoDestino === 'FINALIZADA' && (
              <small style={{ display: 'block' }}>
                Al finalizar, quien no aprobó queda como no aprobado y recibe un aviso en la app. Si hace falta, se puede reabrir con motivo.
              </small>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
              <button type="button" className="btn btn-outline" onClick={() => setEstadoModal(null)}>
                Cancelar
              </button>
              <button type="button" className="btn btn-primary" onClick={handleAdvanceEstado}
                disabled={estadoModal.estado === 'FINALIZADA' && estadoMotivo.trim().length < 5}>
                Confirmar cambio
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Modal Requisitos de la convocatoria */}
      <Modal isOpen={!!reqConv} onClose={() => setReqConv(null)} title={`Requisitos documentales - ${reqConv?.codigo || ''}`} wide>
        {reqConv && reqConv.estado !== 'PLANIFICADA' && (
          <small style={{ display: 'block', marginBottom: '12px' }}>
            Los requisitos solo se cambian mientras la convocatoria está Planificada, para no cambiar las reglas a quien ya se inscribió.
          </small>
        )}
        {reqConv && <RequirementsManager convocatoria={reqConv} editable={reqConv.estado === 'PLANIFICADA'} />}
      </Modal>

      {/* Modal Crear / Editar Curso */}
      <Modal
        isOpen={!!courseModal}
        onClose={() => setCourseModal(null)}
        title={courseModal?.curso ? `Editar curso ${courseModal.curso.codigo}` : 'Nuevo curso preparatorio'}
      >
        {courseModal && (
          <small style={{ display: 'block', marginBottom: '14px' }}>
            Convocatoria: <strong>{courseModal.convocatoria?.codigo} · {courseModal.convocatoria?.nombre}</strong>
          </small>
        )}
        {courseError && <div className="notice-danger" style={{ marginBottom: '14px' }}>{courseError}</div>}
        <form onSubmit={handleSaveCourse}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '12px' }}>
            <div className="form-group">
              <label className="form-label">Código</label>
              <input className="form-input" value={courseForm.codigo} onChange={setCourseField('codigo')} placeholder="CURSO-IA-102" minLength={2} maxLength={50} required />
            </div>
            <div className="form-group">
              <label className="form-label">Nombre</label>
              <input className="form-input" value={courseForm.nombre} onChange={setCourseField('nombre')} placeholder="Estadística para Ciencia de Datos" minLength={3} maxLength={200} required />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Descripción</label>
            <textarea className="form-textarea" rows={3} value={courseForm.descripcion} onChange={setCourseField('descripcion')} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label className="form-label">Puntos totales del curso</label>
              <input type="number" className="form-input" min="1" max="500" step="0.5" value={courseForm.ponderacion_total} onChange={setCourseField('ponderacion_total')} required />
              <small>El tutor crea asignaciones y pruebas hasta llegar a este total.</small>
            </div>
            <div className="form-group">
              <label className="form-label">Nota mínima para aprobar (sobre 100)</label>
              <input type="number" className="form-input" min="0" max="100" step="0.5" value={courseForm.nota_minima} onChange={setCourseField('nota_minima')} required />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Tutor del curso</label>
            <select className="form-select" value={courseForm.tutor_id} onChange={setCourseField('tutor_id')}>
              <option value="">Sin tutor todavía</option>
              {courseTutors.map((t) => (
                <option key={t.usuario_id} value={t.usuario_id} disabled={!t.activo}>
                  {t.nombre_completo} ({t.especialidad}){t.activo ? '' : ' · inactivo'}
                </option>
              ))}
            </select>
            <small style={{ display: 'block', marginTop: '4px' }}>
              {courseTutors.length === 0
                ? 'Ningún tutor trabaja en este programa. El administrador puede agregarlo en Usuarios.'
                : 'Cada curso necesita su tutor para poder abrir la convocatoria.'}
            </small>
          </div>
          {courseModal?.curso?.tutor_id && courseForm.tutor_id && parseInt(courseForm.tutor_id) !== courseModal.curso.tutor_id && (
            <div className="form-group">
              <label className="form-label">Motivo del cambio de tutor *</label>
              <input className="form-input" value={courseForm.motivo_tutor} onChange={setCourseField('motivo_tutor')} minLength={5} required />
            </div>
          )}
          {!courseModal?.curso && (
            <small style={{ display: 'block', marginBottom: '8px' }}>
              El curso se asigna automáticamente a todos los inscritos vigentes de la convocatoria.
            </small>
          )}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn btn-outline" onClick={() => setCourseModal(null)}>Cancelar</button>
            <button type="submit" className="btn btn-primary">{courseModal?.curso ? 'Guardar cambios' : 'Crear curso'}</button>
          </div>
        </form>
      </Modal>

      {/* Modal Crear / Editar Actividad */}
      <Modal
        isOpen={!!actModal}
        onClose={() => setActModal(null)}
        title={actModal?.actividad ? `Editar actividad: ${actModal.actividad.titulo}` : `Nueva actividad para: ${selectedCourse?.nombre}`}
      >
        {actError && <div className="notice-danger" style={{ marginBottom: '14px' }}>{actError}</div>}
        <form onSubmit={handleSaveActivity}>
          {!actModal?.actividad && plantillas.length > 0 && (
            <div className="form-group">
              <label className="form-label">Usar una plantilla del coordinador (opcional)</label>
              <select className="form-select" defaultValue="" onChange={(e) => usarPlantilla(e.target.value)}>
                <option value="">Crear desde cero</option>
                {plantillas.map((p) => (
                  <option key={p.id} value={p.id}>{p.titulo} · {p.ponderacion} pts</option>
                ))}
              </select>
            </div>
          )}
          <div className="form-group">
            <label className="form-label">Título de la actividad o proyecto</label>
            <input className="form-input" placeholder="Ej. Taller 3: Optimización Matemática..." value={actForm.titulo} onChange={setActField('titulo')} minLength={3} maxLength={200} required />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label className="form-label">Tipo</label>
              <select className="form-select" value={actForm.tipo} onChange={setActField('tipo')}>
                {TIPOS_ACTIVIDAD.map((t) => <option key={t.valor} value={t.valor}>{t.texto}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Puntos</label>
              <input type="number" className="form-input" min="0.5" max="100" step="0.5" value={actForm.ponderacion} onChange={setActField('ponderacion')} required />
            </div>
            <div className="form-group">
              <label className="form-label">Apertura</label>
              <input type="datetime-local" className="form-input" value={actForm.fecha_apertura} onChange={setActField('fecha_apertura')} required />
            </div>
            <div className="form-group">
              <label className="form-label">Fecha límite</label>
              <input type="datetime-local" className="form-input" value={actForm.fecha_limite} min={actForm.fecha_apertura} onChange={setActField('fecha_limite')} required />
            </div>
            <div className="form-group">
              <label className="form-label">Formatos (separados por coma)</label>
              <input className="form-input" value={actForm.extensiones_permitidas} onChange={setActField('extensiones_permitidas')} required />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div className="form-group">
                <label className="form-label">Máx. MB</label>
                <input type="number" className="form-input" min="1" max="50" value={actForm.tamano_max_mb} onChange={setActField('tamano_max_mb')} required />
              </div>
              <div className="form-group">
                <label className="form-label">Envíos</label>
                <input type="number" className="form-input" min="1" max="10" value={actForm.max_reenvios} onChange={setActField('max_reenvios')} required />
              </div>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Instrucciones</label>
            <textarea className="form-textarea" rows={3} placeholder="Objetivos, pautas de entrega y rúbrica..." value={actForm.instrucciones} onChange={setActField('instrucciones')} />
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem' }}>
            <input type="checkbox" checked={actForm.es_obligatorio} onChange={setActField('es_obligatorio')} />
            Obligatoria para aprobar el curso
          </label>

          <small style={{ display: 'block', marginTop: '10px' }}>
            Puntos disponibles en el curso: {totalCurso - sumaPonderaciones + (actModal?.actividad ? parseFloat(actModal.actividad.ponderacion) : 0)} de {totalCurso}.
            Estándar: asignación {puntosEstandar.ASIGNACION} y prueba {puntosEstandar.PRUEBA} puntos.
          </small>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn btn-outline" onClick={() => setActModal(null)}>Cancelar</button>
            <button type="submit" className="btn btn-primary">{actModal?.actividad ? 'Guardar cambios' : 'Crear actividad'}</button>
          </div>
        </form>
      </Modal>

      {/* Modal Plantillas del programa */}
      <Modal isOpen={tplModal} onClose={() => setTplModal(false)} title="Plantillas de actividades del programa">
        <small style={{ display: 'block', marginBottom: '12px' }}>
          Los tutores pueden usarlas al crear actividades en sus cursos, o crear las suyas.
        </small>
        {tplError && <div className="notice-danger" style={{ marginBottom: '14px' }}>{tplError}</div>}
        {plantillas.length === 0 ? (
          <p style={{ color: 'var(--text-sec)' }}>Todavía no hay plantillas.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
            {plantillas.map((p) => (
              <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', padding: '10px 12px', border: '1px solid var(--border-light)', borderRadius: '10px' }}>
                <div>
                  <strong>{p.titulo}</strong> <Badge type={p.tipo} />
                  <div><small>{p.ponderacion} puntos · formatos {p.extensiones_permitidas}</small></div>
                </div>
                <button className="btn btn-outline" style={{ padding: '6px 8px' }} title="Eliminar plantilla" onClick={() => handleDeleteTemplate(p.id)}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
        <form onSubmit={handleSaveTemplate} style={{ borderTop: '1px solid var(--border-light)', paddingTop: '14px' }}>
          <h4 style={{ marginBottom: '10px' }}>Nueva plantilla</h4>
          <div className="form-group">
            <label className="form-label">Título</label>
            <input className="form-input" value={tplForm.titulo} onChange={(e) => setTplForm({ ...tplForm, titulo: e.target.value })} minLength={2} required />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
            <div className="form-group">
              <label className="form-label">Tipo</label>
              <select className="form-select" value={tplForm.tipo}
                onChange={(e) => setTplForm({ ...tplForm, tipo: e.target.value, ponderacion: puntosEstandar[e.target.value] || tplForm.ponderacion })}>
                {TIPOS_ACTIVIDAD.map((t) => <option key={t.valor} value={t.valor}>{t.texto}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Puntos</label>
              <input type="number" className="form-input" min="0.5" max="100" step="0.5" value={tplForm.ponderacion} onChange={(e) => setTplForm({ ...tplForm, ponderacion: e.target.value })} required />
            </div>
            <div className="form-group">
              <label className="form-label">Formatos</label>
              <input className="form-input" value={tplForm.extensiones_permitidas} onChange={(e) => setTplForm({ ...tplForm, extensiones_permitidas: e.target.value })} required />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Instrucciones</label>
            <textarea className="form-textarea" rows={2} value={tplForm.instrucciones} onChange={(e) => setTplForm({ ...tplForm, instrucciones: e.target.value })} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button type="submit" className="btn btn-primary">Agregar plantilla</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
