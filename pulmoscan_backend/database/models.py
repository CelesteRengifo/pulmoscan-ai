"""
PulmoScan AI — Modelos de base de datos
SQLAlchemy ORM + SQLite (dev) / PostgreSQL (prod)

Tablas:
  pacientes        — datos demográficos del paciente
  estudios         — cada radiografía cargada al sistema
  resultados_modelo — salida del modelo para cada estudio
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Float, Boolean,
    Text, Enum, ForeignKey, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


# ──────────────────────────────────────────────────────────────────────────────
#  Base
# ──────────────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


def _now_utc():
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────────────────────────────────────
#  Enums
# ──────────────────────────────────────────────────────────────────────────────

class SexoEnum(str, enum.Enum):
    masculino  = "M"
    femenino   = "F"
    otro       = "O"
    no_indica  = "N"

class TipoDocumentoEnum(str, enum.Enum):
    dni        = "DNI"
    pasaporte  = "PASAPORTE"
    rut        = "RUT"
    cedula     = "CEDULA"
    otro       = "OTRO"

class EstadoEstudioEnum(str, enum.Enum):
    pendiente  = "PENDIENTE"   # imagen cargada, sin procesar aún
    procesado  = "PROCESADO"   # modelo ejecutado con éxito
    error      = "ERROR"       # falló la inferencia
    revisado   = "REVISADO"    # un clínico lo marcó como revisado

class LabelResultadoEnum(str, enum.Enum):
    tb         = "TB"
    normal     = "NORMAL"

class NivelConfianzaEnum(str, enum.Enum):
    alta       = "alta"
    moderada   = "moderada"
    baja       = "baja"


# ──────────────────────────────────────────────────────────────────────────────
#  Tabla 1: Pacientes
# ──────────────────────────────────────────────────────────────────────────────

class Paciente(Base):
    __tablename__ = "pacientes"

    # ── Clave primaria ──
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Identificación ──
    tipo_documento  = Column(Enum(TipoDocumentoEnum), nullable=True)
    numero_documento = Column(String(30), nullable=True, index=True)

    # ── Datos personales ──
    nombres         = Column(String(100), nullable=False)
    apellidos       = Column(String(100), nullable=False)
    fecha_nacimiento = Column(Date, nullable=True)
    sexo            = Column(Enum(SexoEnum), nullable=True)

    # ── Contacto ──
    telefono        = Column(String(20),  nullable=True)
    direccion       = Column(String(255), nullable=True)

    # ── Contacto de emergencia ──
    contacto_nombre    = Column(String(150), nullable=True)
    contacto_telefono  = Column(String(20),  nullable=True)
    contacto_relacion  = Column(String(50),  nullable=True)   # ej: "madre", "cónyuge"

    # ── Notas clínicas libres ──
    notas           = Column(Text, nullable=True)

    # ── Auditoría ──
    creado_en       = Column(DateTime(timezone=True), default=_now_utc, nullable=False)
    actualizado_en  = Column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False)
    activo          = Column(Boolean, default=True, nullable=False)   # soft delete

    # ── Restricciones ──
    __table_args__ = (
        UniqueConstraint("tipo_documento", "numero_documento", name="uq_paciente_documento"),
    )

    # ── Relación ──
    estudios = relationship("Estudio", back_populates="paciente", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Paciente id={self.id} nombre='{self.nombres} {self.apellidos}'>"

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"


# ──────────────────────────────────────────────────────────────────────────────
#  Tabla 2: Estudios  (una radiografía cargada = un estudio)
# ──────────────────────────────────────────────────────────────────────────────

class Estudio(Base):
    __tablename__ = "estudios"

    # ── Clave primaria ──
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Relación con paciente ──
    paciente_id = Column(Integer, ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Datos del estudio ──
    fecha_estudio   = Column(Date,    nullable=False)             # fecha en que se tomó la Rx
    fecha_carga     = Column(DateTime(timezone=True), default=_now_utc, nullable=False)  # cuando se subió al sistema

    # ── Archivo ──
    nombre_archivo_original = Column(String(255), nullable=True)  # nombre que subió el usuario
    ruta_imagen     = Column(String(512), nullable=True)          # path o URL de almacenamiento
    formato_imagen  = Column(String(10),  nullable=True)          # jpg, png, dicom...
    tamanio_bytes   = Column(Integer,     nullable=True)
    resolucion_px   = Column(String(20),  nullable=True)          # ej: "1024x1024"

    # ── Contexto clínico ──
    motivo_consulta = Column(Text, nullable=True)
    medico_solicitante = Column(String(150), nullable=True)
    institucion     = Column(String(150), nullable=True)

    # ── Estado ──
    estado          = Column(Enum(EstadoEstudioEnum), default=EstadoEstudioEnum.pendiente, nullable=False)
    notas           = Column(Text, nullable=True)

    # ── Auditoría ──
    creado_en       = Column(DateTime(timezone=True), default=_now_utc, nullable=False)
    actualizado_en  = Column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False)

    # ── Relaciones ──
    paciente        = relationship("Paciente", back_populates="estudios")
    resultado       = relationship("ResultadoModelo", back_populates="estudio", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Estudio id={self.id} paciente_id={self.paciente_id} fecha={self.fecha_estudio} estado={self.estado}>"


# ──────────────────────────────────────────────────────────────────────────────
#  Tabla 3: Resultados del modelo
# ──────────────────────────────────────────────────────────────────────────────

class ResultadoModelo(Base):
    __tablename__ = "resultados_modelo"

    # ── Clave primaria ──
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Relación con estudio ──
    estudio_id = Column(Integer, ForeignKey("estudios.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # ── Resultado principal ──
    label           = Column(Enum(LabelResultadoEnum), nullable=False)   # "TB" | "NORMAL"
    prob_tb         = Column(Float, nullable=False)                       # 0.0 – 1.0
    prob_normal     = Column(Float, nullable=False)
    threshold       = Column(Float, nullable=False)                       # umbral usado
    nivel_confianza = Column(Enum(NivelConfianzaEnum), nullable=False)    # alta/moderada/baja

    # ── Interpretación generada ──
    interpretacion  = Column(Text, nullable=True)    # texto descriptivo del resultado

    # ── Técnico: pipeline ──
    backbone              = Column(String(30),  nullable=True)   # densenet169 / efficientnet_b4
    version_modelo        = Column(String(20),  nullable=True)   # versión del .pt o del sistema
    enhancement_mode      = Column(String(30),  nullable=True)   # clahe_gamma, etc.
    segmentacion_usada    = Column(Boolean,     nullable=True)   # si el U-Net procesó la imagen
    resolucion_entrada_modelo = Column(String(20), nullable=True) # ej: "380x380"

    # ── Tiempos ──
    tiempo_procesamiento_ms = Column(Float, nullable=True)       # ms totales del pipeline
    procesado_en          = Column(DateTime(timezone=True), default=_now_utc, nullable=False)

    # ── Revisión clínica ──
    revisado_por          = Column(String(100), nullable=True)   # médico que revisó
    fecha_revision        = Column(DateTime(timezone=True), nullable=True)
    conclusion_clinica    = Column(Text, nullable=True)          # criterio del especialista
    concordancia_modelo   = Column(Boolean, nullable=True)       # ¿el clínico estuvo de acuerdo?

    # ── Restricciones ──
    __table_args__ = (
        CheckConstraint("prob_tb >= 0.0 AND prob_tb <= 1.0", name="ck_prob_tb_rango"),
        CheckConstraint("prob_normal >= 0.0 AND prob_normal <= 1.0", name="ck_prob_normal_rango"),
        CheckConstraint("threshold >= 0.0 AND threshold <= 1.0", name="ck_threshold_rango"),
    )

    # ── Relación ──
    estudio = relationship("Estudio", back_populates="resultado")

    def __repr__(self):
        return (
            f"<ResultadoModelo id={self.id} estudio_id={self.estudio_id} "
            f"label={self.label} prob_tb={self.prob_tb:.3f}>"
        )
