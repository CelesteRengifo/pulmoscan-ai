"""
PulmoScan AI — Operaciones CRUD
Funciones reutilizables para pacientes, estudios y resultados.
"""

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from .models import (
    Paciente, Estudio, ResultadoModelo,
    EstadoEstudioEnum, LabelResultadoEnum, NivelConfianzaEnum,
    SexoEnum, TipoDocumentoEnum,
)


# ──────────────────────────────────────────────────────────────────────────────
#  Pacientes
# ──────────────────────────────────────────────────────────────────────────────

def crear_paciente(
    db: Session,
    nombres: str,
    apellidos: str,
    fecha_nacimiento: Optional[date] = None,
    sexo: Optional[SexoEnum] = None,
    tipo_documento: Optional[TipoDocumentoEnum] = None,
    numero_documento: Optional[str] = None,
    telefono: Optional[str] = None,
    direccion: Optional[str] = None,
    contacto_nombre: Optional[str] = None,
    contacto_telefono: Optional[str] = None,
    contacto_relacion: Optional[str] = None,
    notas: Optional[str] = None,
) -> Paciente:
    paciente = Paciente(
        nombres=nombres,
        apellidos=apellidos,
        fecha_nacimiento=fecha_nacimiento,
        sexo=sexo,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        telefono=telefono,
        direccion=direccion,
        contacto_nombre=contacto_nombre,
        contacto_telefono=contacto_telefono,
        contacto_relacion=contacto_relacion,
        notas=notas,
    )
    db.add(paciente)
    db.commit()
    db.refresh(paciente)
    return paciente


def obtener_paciente(db: Session, paciente_id: int) -> Optional[Paciente]:
    return db.query(Paciente).filter(Paciente.id == paciente_id, Paciente.activo == True).first()


def buscar_pacientes(db: Session, texto: str, limite: int = 20) -> list[Paciente]:
    """Búsqueda por nombre, apellido o número de documento."""
    q = f"%{texto}%"
    return (
        db.query(Paciente)
        .filter(
            Paciente.activo == True,
            (Paciente.nombres.ilike(q))
            | (Paciente.apellidos.ilike(q))
            | (Paciente.numero_documento.ilike(q)),
        )
        .limit(limite)
        .all()
    )


def listar_pacientes(db: Session, skip: int = 0, limit: int = 50) -> list[Paciente]:
    return db.query(Paciente).filter(Paciente.activo == True).offset(skip).limit(limit).all()


def actualizar_paciente(db: Session, paciente_id: int, **campos) -> Optional[Paciente]:
    paciente = obtener_paciente(db, paciente_id)
    if not paciente:
        return None
    for campo, valor in campos.items():
        if hasattr(paciente, campo) and valor is not None:
            setattr(paciente, campo, valor)
    db.commit()
    db.refresh(paciente)
    return paciente


def eliminar_paciente(db: Session, paciente_id: int) -> bool:
    """Soft delete — marca como inactivo."""
    paciente = obtener_paciente(db, paciente_id)
    if not paciente:
        return False
    paciente.activo = False
    db.commit()
    return True


# ──────────────────────────────────────────────────────────────────────────────
#  Estudios
# ──────────────────────────────────────────────────────────────────────────────

def crear_estudio(
    db: Session,
    paciente_id: int,
    fecha_estudio: date,
    nombre_archivo_original: Optional[str] = None,
    ruta_imagen: Optional[str] = None,
    formato_imagen: Optional[str] = None,
    tamanio_bytes: Optional[int] = None,
    resolucion_px: Optional[str] = None,
    motivo_consulta: Optional[str] = None,
    medico_solicitante: Optional[str] = None,
    institucion: Optional[str] = None,
    notas: Optional[str] = None,
) -> Estudio:
    estudio = Estudio(
        paciente_id=paciente_id,
        fecha_estudio=fecha_estudio,
        nombre_archivo_original=nombre_archivo_original,
        ruta_imagen=ruta_imagen,
        formato_imagen=formato_imagen,
        tamanio_bytes=tamanio_bytes,
        resolucion_px=resolucion_px,
        motivo_consulta=motivo_consulta,
        medico_solicitante=medico_solicitante,
        institucion=institucion,
        notas=notas,
        estado=EstadoEstudioEnum.pendiente,
    )
    db.add(estudio)
    db.commit()
    db.refresh(estudio)
    return estudio


def obtener_estudio(db: Session, estudio_id: int) -> Optional[Estudio]:
    return db.query(Estudio).filter(Estudio.id == estudio_id).first()


def listar_estudios_paciente(db: Session, paciente_id: int) -> list[Estudio]:
    return (
        db.query(Estudio)
        .filter(Estudio.paciente_id == paciente_id)
        .order_by(Estudio.fecha_estudio.desc())
        .all()
    )


def actualizar_estado_estudio(db: Session, estudio_id: int, estado: EstadoEstudioEnum) -> Optional[Estudio]:
    estudio = obtener_estudio(db, estudio_id)
    if not estudio:
        return None
    estudio.estado = estado
    db.commit()
    db.refresh(estudio)
    return estudio

def listar_estudios(db: Session, resultado_filtro: Optional[str] = None):
    from database.models import Estudio, ResultadoModelo
    q = db.query(Estudio).join(ResultadoModelo, isouter=True)
    if resultado_filtro:
        q = q.filter(ResultadoModelo.label == resultado_filtro)
    return q.order_by(Estudio.creado_en.desc()).all()

# ──────────────────────────────────────────────────────────────────────────────
#  Resultados del modelo
# ──────────────────────────────────────────────────────────────────────────────

def crear_resultado(
    db: Session,
    estudio_id: int,
    label: str,                    # "TB" | "NORMAL"
    prob_tb: float,
    prob_normal: float,
    threshold: float,
    nivel_confianza: str,          # "alta" | "moderada" | "baja"
    interpretacion: Optional[str] = None,
    backbone: Optional[str] = None,
    version_modelo: Optional[str] = None,
    enhancement_mode: Optional[str] = None,
    segmentacion_usada: Optional[bool] = None,
    resolucion_entrada_modelo: Optional[str] = None,
    tiempo_procesamiento_ms: Optional[float] = None,
) -> ResultadoModelo:
    resultado = ResultadoModelo(
        estudio_id=estudio_id,
        label=LabelResultadoEnum(label),
        prob_tb=prob_tb,
        prob_normal=prob_normal,
        threshold=threshold,
        nivel_confianza=NivelConfianzaEnum(nivel_confianza),
        interpretacion=interpretacion,
        backbone=backbone,
        version_modelo=version_modelo,
        enhancement_mode=enhancement_mode,
        segmentacion_usada=segmentacion_usada,
        resolucion_entrada_modelo=resolucion_entrada_modelo,
        tiempo_procesamiento_ms=tiempo_procesamiento_ms,
    )
    db.add(resultado)
    # Marcar estudio como procesado
    estudio = obtener_estudio(db, estudio_id)
    if estudio:
        estudio.estado = EstadoEstudioEnum.procesado
    db.commit()
    db.refresh(resultado)
    return resultado


def obtener_resultado_por_estudio(db: Session, estudio_id: int) -> Optional[ResultadoModelo]:
    return db.query(ResultadoModelo).filter(ResultadoModelo.estudio_id == estudio_id).first()


def agregar_revision_clinica(
    db: Session,
    estudio_id: int,
    revisado_por: str,
    conclusion_clinica: str,
    concordancia_modelo: bool,
) -> Optional[ResultadoModelo]:
    """El médico registra su criterio clínico sobre el resultado del modelo."""
    resultado = obtener_resultado_por_estudio(db, estudio_id)
    if not resultado:
        return None
    resultado.revisado_por       = revisado_por
    resultado.fecha_revision     = datetime.now(timezone.utc)
    resultado.conclusion_clinica = conclusion_clinica
    resultado.concordancia_modelo = concordancia_modelo
    # Actualizar estado del estudio
    estudio = obtener_estudio(db, estudio_id)
    if estudio:
        estudio.estado = EstadoEstudioEnum.revisado
    db.commit()
    db.refresh(resultado)
    return resultado


# ──────────────────────────────────────────────────────────────────────────────
#  Estadísticas generales (para el Dashboard)
# ──────────────────────────────────────────────────────────────────────────────

def estadisticas_generales(
    db: Session,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> dict:
    """
    Calcula métricas agregadas para el dashboard:
    total de pacientes, estudios, casos TB/NORMAL y porcentaje de TB detectado.

    Si se especifica fecha_desde y/o fecha_hasta, los estudios y resultados
    se filtran por Estudio.fecha_estudio dentro de ese rango (inclusive).
    total_pacientes NO se filtra por fecha — siempre refleja el total de
    pacientes activos registrados en el sistema.
    """
    total_pacientes = db.query(Paciente).filter(Paciente.activo == True).count()

    # ── Query base de estudios, con filtro de fecha opcional ──
    q_estudios = db.query(Estudio)
    if fecha_desde is not None:
        q_estudios = q_estudios.filter(Estudio.fecha_estudio >= fecha_desde)
    if fecha_hasta is not None:
        q_estudios = q_estudios.filter(Estudio.fecha_estudio <= fecha_hasta)

    total_estudios = q_estudios.count()

    estudios_pendientes = q_estudios.filter(Estudio.estado == EstadoEstudioEnum.pendiente).count()
    estudios_revisados  = q_estudios.filter(Estudio.estado == EstadoEstudioEnum.revisado).count()

    # ── Resultados unidos a estudio para poder filtrar por fecha_estudio ──
    q_resultados = db.query(ResultadoModelo).join(Estudio, ResultadoModelo.estudio_id == Estudio.id)
    if fecha_desde is not None:
        q_resultados = q_resultados.filter(Estudio.fecha_estudio >= fecha_desde)
    if fecha_hasta is not None:
        q_resultados = q_resultados.filter(Estudio.fecha_estudio <= fecha_hasta)

    total_tb     = q_resultados.filter(ResultadoModelo.label == LabelResultadoEnum.tb).count()
    total_normal = q_resultados.filter(ResultadoModelo.label == LabelResultadoEnum.normal).count()
    total_resultados = total_tb + total_normal

    porcentaje_tb = round((total_tb / total_resultados) * 100, 1) if total_resultados > 0 else 0.0

    return {
        "total_pacientes":      total_pacientes,
        "total_estudios":       total_estudios,
        "total_tb":             total_tb,
        "total_normal":         total_normal,
        "porcentaje_tb":        porcentaje_tb,
        "estudios_pendientes":  estudios_pendientes,
        "estudios_revisados":   estudios_revisados,
        "fecha_desde":          fecha_desde.isoformat() if fecha_desde else None,
        "fecha_hasta":          fecha_hasta.isoformat() if fecha_hasta else None,
    }