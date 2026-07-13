"""
PulmoScan AI — Backend FastAPI
Integrado con base de datos SQLAlchemy.

Endpoints:
  GET  /health
  GET  /estadisticas            ← totales para el dashboard
  POST /predict/{paciente_id}   ← analiza y guarda resultado en BD
  POST /pacientes               ← crea paciente
  GET  /pacientes               ← lista pacientes
  GET  /pacientes/{id}          ← detalle + historial de estudios
  GET  /estudios/{id}           ← estudio + resultado del modelo
  GET  /estudios/{id}/imagenes  ← imágenes del procesamiento
"""

import io
import os
import time
import logging
import traceback
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import cv2
from PIL import Image

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database.reporte import generar_reporte_pdf
from fastapi.responses import StreamingResponse

from database import get_db, create_tables
from database import crud
from database.models import SexoEnum, TipoDocumentoEnum

# ── Importar desde train.py (igual que el backend anterior) ──────────────────
from train import (
    NeuralLungSegmentationEnhancer,
    ScoreCAM,
    _overlay_cam_on_gray,
    build_enhancer,
)
# ── Importar load_classifier desde classifier_model.py (igual que el anterior)
from classifier_model import load_classifier

# ──────────────────────────────────────────────────────────────────────────────
#  Configuración
# ──────────────────────────────────────────────────────────────────────────────

VERSION = "1.0.0-demo"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
MAX_FILE_SIZE_MB = 10

MODEL_DIR       = Path("models")
CLASSIFIER_PATH = MODEL_DIR / "densenet_169_tb_best.pt"
SEGMENTER_PATH  = MODEL_DIR / "lung_attention_unet_best.pt"

STATIC_DIR = Path("static/estudios")
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Threshold override via variable de entorno
# Ejemplo en PowerShell: $env:TB_THRESHOLD="0.60"
_ENV_THRESHOLD = os.environ.get("TB_THRESHOLD")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("pulmoscan")

# ──────────────────────────────────────────────────────────────────────────────
#  Pipeline global (se carga UNA sola vez al iniciar — igual que backend anterior)
# ──────────────────────────────────────────────────────────────────────────────

device     = torch.device("cpu")
clf        = {}          # dict con model, threshold, img_size, mean, std, etc.
lung_seg   = None        # NeuralLungSegmentationEnhancer
score_cam  = None        # ScoreCAM inicializado una sola vez (más eficiente)
enhancer   = None        # build_enhancer con parámetros del checkpoint
transform  = None        # torchvision transform


def _get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    try:
        import torch_directml  # type: ignore
        return torch_directml.device()
    except ImportError:
        return torch.device("cpu")


def load_models():
    global device, clf, lung_seg, score_cam, enhancer, transform

    device = _get_device()

    # ── 1. Clasificador via load_classifier() (igual que backend anterior) ───
    if not CLASSIFIER_PATH.exists():
        log.error(f"Clasificador no encontrado: {CLASSIFIER_PATH}"); return

    clf = load_classifier(str(CLASSIFIER_PATH), device)

    # ── Threshold: checkpoint o variable de entorno ───────────────────────────
    threshold_ckpt = float(clf["threshold"])
    if _ENV_THRESHOLD is not None:
        try:
            threshold_final = float(_ENV_THRESHOLD)
            log.warning(
                f"[THRESHOLD] Sobreescrito por TB_THRESHOLD: "
                f"{threshold_ckpt:.4f} → {threshold_final:.4f}"
            )
            clf["threshold"] = threshold_final
        except ValueError:
            log.error(f"TB_THRESHOLD='{_ENV_THRESHOLD}' inválido, se usa el del checkpoint.")
            threshold_final = threshold_ckpt
    else:
        threshold_final = threshold_ckpt

    # ── 2. Segmentador via NeuralLungSegmentationEnhancer (igual que anterior)
    lung_seg = NeuralLungSegmentationEnhancer(
        checkpoint_path=str(SEGMENTER_PATH),
        outside_scale=clf.get("lung_segmentation_outside_scale", 0.08),
        fallback="heuristic",
    )

    # ── 3. Score-CAM inicializado UNA sola vez y reutilizado (igual que anterior)
    score_cam = ScoreCAM(
        model=clf["model"],
        target_layer=clf["model"].features[-1],
        max_maps=32,
        batch_size=8,
        activation_quantile=0.70,
    )

    # ── 4. build_enhancer con parámetros del checkpoint (igual que anterior) ──
    emode = clf.get("enhancement_mode", "clahe_gamma")
    enhancer = build_enhancer(
        mode=emode,
        clahe_clip_limit=clf.get("clahe_clip_limit", 2.0),
        clahe_tile_grid=clf.get("clahe_tile_grid", 8),
        gamma=clf.get("gamma", 1.1),
    )

    # ── 5. Transform ──────────────────────────────────────────────────────────
    transform = transforms.Compose([
        transforms.Resize((clf["img_size"], clf["img_size"])),
        transforms.Lambda(lambda x: x.convert("RGB")),
        transforms.ToTensor(),
        transforms.Normalize(mean=clf["mean"], std=clf["std"]),
    ])

    # ── Log de diagnóstico al arrancar ───────────────────────────────────────
    log.info("=" * 60)
    log.info(f"[MODEL] backbone          = {clf.get('backbone', 'densenet169')}")
    log.info(f"[MODEL] img_size          = {clf['img_size']}")
    log.info(f"[MODEL] tb_index          = {clf['tb_index']}")
    log.info(f"[MODEL] enhancement_mode  = {emode}")
    log.info(f"[MODEL] clahe_clip_limit  = {clf.get('clahe_clip_limit', 2.0)}")
    log.info(f"[MODEL] clahe_tile_grid   = {clf.get('clahe_tile_grid', 8)}")
    log.info(f"[MODEL] gamma             = {clf.get('gamma', 1.1)}")
    log.info(f"[MODEL] outside_scale     = {clf.get('lung_segmentation_outside_scale', 0.08)}")
    log.info(f"[MODEL] threshold (ckpt)  = {threshold_ckpt:.4f}")
    log.info(f"[MODEL] threshold (usado) = {threshold_final:.4f}")
    log.info(f"[MODEL] mean              = {clf['mean']}")
    log.info(f"[MODEL] std               = {clf['std']}")
    log.info("=" * 60)
    log.info("Pipeline listo ✔  (ScoreCAM inicializado una sola vez)")

# ──────────────────────────────────────────────────────────────────────────────
#  Guardar imágenes del procesamiento
# ──────────────────────────────────────────────────────────────────────────────

def _save_imagenes_estudio(estudio_id: int, result: dict) -> None:
    folder = STATIC_DIR / str(estudio_id)
    folder.mkdir(parents=True, exist_ok=True)

    result["_img_original"].convert("RGB").save(
        folder / "original.jpg", format="JPEG", quality=90)
    result["_img_clahe"].convert("RGB").save(
        folder / "clahe.jpg", format="JPEG", quality=90)

    seg = result.get("_img_segmentacion") or result["_img_original"]
    seg.convert("RGB").save(folder / "segmentacion.jpg", format="JPEG", quality=90)

    result["_img_scorecam"].convert("RGB").save(
        folder / "scorecam.jpg", format="JPEG", quality=90)

# ──────────────────────────────────────────────────────────────────────────────
#  Pipeline de inferencia (lógica idéntica al backend anterior)
# ──────────────────────────────────────────────────────────────────────────────

def run_inference(image_bytes: bytes) -> dict:
    img_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_pil.load()
    w, h = img_pil.size

    if w < 64 or h < 64:
        raise ValueError("Imagen demasiado pequeña (mínimo 64×64 px).")
    if w > 6000 or h > 6000:
        raise ValueError("Imagen demasiado grande (máximo 6000×6000 px).")

    # 1 · Mejora de imagen con parámetros del checkpoint (igual que anterior)
    enhanced_pil = enhancer(img_pil.convert("L")) if enhancer else img_pil.convert("L")
    img_clahe    = enhanced_pil.copy()

    # 2 · Segmentación pulmonar via NeuralLungSegmentationEnhancer
    enhanced_np = np.array(enhanced_pil.convert("L"), dtype=np.uint8)
    full_mask   = lung_seg.predict_mask(enhanced_np)
    lung_pil    = lung_seg(enhanced_pil)          # imagen con máscara aplicada
    img_segmentacion = lung_pil.copy()

    # 3 · Clasificación
    tensor = transform(lung_pil).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = clf["model"](tensor)
        probs  = torch.softmax(logits, 1)[0]
    prob_tb     = float(probs[clf["tb_index"]])
    prob_normal = 1.0 - prob_tb

    # 4 · Score-CAM reutilizando la instancia global (más eficiente)
    sz      = (clf["img_size"], clf["img_size"])
    mask_r  = cv2.resize(full_mask, sz, interpolation=cv2.INTER_NEAREST)
    cam_map = score_cam.compute(tensor, class_idx=clf["tb_index"], region_mask=mask_r)

    gray_np  = np.array(img_pil.convert("L"), dtype=np.uint8)
    overlay  = _overlay_cam_on_gray(
        gray=gray_np, cam_map=cam_map, restrict_mask=mask_r,
        sigma=7.0, low_pct=12.0, high_pct=99.5, threshold=0.08, alpha=0.55,
    )
    img_scorecam = Image.fromarray(overlay, mode="RGB")

    threshold = clf["threshold"]
    label     = "TB" if prob_tb >= threshold else "NORMAL"

    # Log por predicción
    log.info(
        f"[PRED] prob_tb={prob_tb:.4f} | prob_normal={prob_normal:.4f} | "
        f"threshold={threshold:.4f} | label={label}"
    )

    img_size = clf["img_size"]
    return dict(
        label=label,
        prob_tb=round(prob_tb, 4),
        prob_normal=round(prob_normal, 4),
        threshold=threshold,
        segmentation_used=True,
        image_size_input=[w, h],
        image_size_model=[img_size, img_size],
        enhancement_mode=clf.get("enhancement_mode", "clahe_gamma"),
        backbone=clf.get("backbone", "densenet169"),
        _img_original=img_pil,
        _img_clahe=img_clahe,
        _img_segmentacion=img_segmentacion,
        _img_scorecam=img_scorecam,
    )


def _confidence(p: float) -> str:
    if p >= 0.80 or p <= 0.20: return "alta"
    if p >= 0.65 or p <= 0.35: return "moderada"
    return "baja"


def _interpretation(label: str, p: float) -> str:
    if label == "TB":
        return (f"La radiografía presenta hallazgos compatibles con tuberculosis pulmonar "
                f"(probabilidad {p*100:.1f}%). Se recomienda evaluación clínica especializada.")
    return (f"No se detectaron hallazgos sugestivos de tuberculosis pulmonar "
            f"(probabilidad TB: {p*100:.1f}%). Esto no descarta otras patologías.")

# ──────────────────────────────────────────────────────────────────────────────
#  FastAPI
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PulmoScan AI API",
    description=(
        "API de detección de Tuberculosis Pulmonar mediante análisis de radiografías de tórax. "
        "**Solo para uso como prototipo de apoyo diagnóstico.** "
        "No reemplaza el criterio clínico especializado."
    ),
    version=VERSION,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    create_tables()
    load_models()

# ──────────────────────────────────────────────────────────────────────────────
#  Schemas Pydantic
# ──────────────────────────────────────────────────────────────────────────────

class PacienteCreate(BaseModel):
    nombres:           str            = Field(..., min_length=1, max_length=100)
    apellidos:         str            = Field(..., min_length=1, max_length=100)
    fecha_nacimiento:  Optional[date] = None
    sexo:              Optional[str]  = None
    tipo_documento:    Optional[str]  = None
    numero_documento:  Optional[str]  = None
    telefono:          Optional[str]  = None
    direccion:         Optional[str]  = None
    contacto_nombre:   Optional[str]  = None
    contacto_telefono: Optional[str]  = None
    contacto_relacion: Optional[str]  = None
    notas:             Optional[str]  = None

class PacienteOut(BaseModel):
    id:                int
    nombres:           str
    apellidos:         str
    fecha_nacimiento:  Optional[date]
    sexo:              Optional[str]
    tipo_documento:    Optional[str]
    numero_documento:  Optional[str]
    telefono:          Optional[str]
    direccion:         Optional[str]
    contacto_nombre:   Optional[str]
    contacto_telefono: Optional[str]
    contacto_relacion: Optional[str]
    notas:             Optional[str]
    creado_en:         datetime
    class Config: from_attributes = True

class ResultadoOut(BaseModel):
    id:                        int
    estudio_id:                int
    label:                     str
    prob_tb:                   float
    prob_normal:               float
    threshold:                 float
    nivel_confianza:           str
    interpretacion:            Optional[str]
    backbone:                  Optional[str]
    version_modelo:            Optional[str]
    enhancement_mode:          Optional[str]
    segmentacion_usada:        Optional[bool]
    resolucion_entrada_modelo: Optional[str]
    tiempo_procesamiento_ms:   Optional[float]
    procesado_en:              datetime
    revisado_por:              Optional[str]
    fecha_revision:            Optional[datetime]
    conclusion_clinica:        Optional[str]
    concordancia_modelo:       Optional[bool]
    class Config: from_attributes = True

class EstudioOut(BaseModel):
    id:                      int
    paciente_id:             int
    fecha_estudio:           date
    fecha_carga:             datetime
    nombre_archivo_original: Optional[str]
    formato_imagen:          Optional[str]
    tamanio_bytes:           Optional[int]
    resolucion_px:           Optional[str]
    motivo_consulta:         Optional[str]
    medico_solicitante:      Optional[str]
    institucion:             Optional[str]
    estado:                  str
    notas:                   Optional[str]
    resultado:               Optional[ResultadoOut]
    class Config: from_attributes = True

class PacienteDetalle(PacienteOut):
    estudios: list[EstudioOut] = []

class PredictResponse(BaseModel):
    label:              str
    prob_tb:            float
    prob_normal:        float
    threshold:          float
    interpretation:     str
    confidence_level:   str
    disclaimer:         str
    backbone:           str
    enhancement_mode:   str
    segmentation_used:  bool
    image_size_input:   list[int]
    image_size_model:   list[int]
    estudio_id:         int
    resultado_id:       int
    version:            str
    timestamp:          str
    processing_time_ms: float

class HealthResponse(BaseModel):
    status:               str
    version:              str
    timestamp:            str
    models_loaded:        bool
    classifier_backbone:  Optional[str]
    segmenter_loaded:     bool
    threshold_used:       Optional[float]

class ImagenesEstudioOut(BaseModel):
    original:     str
    clahe:        str
    segmentacion: str
    scorecam:     str

class EstadisticasOut(BaseModel):
    total_pacientes:     int
    total_estudios:      int
    total_tb:            int
    total_normal:        int
    porcentaje_tb:       float
    estudios_pendientes: int
    estudios_revisados:  int
    fecha_desde:         Optional[str] = None
    fecha_hasta:         Optional[str] = None

# ──────────────────────────────────────────────────────────────────────────────
#  Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "PulmoScan AI API", "version": VERSION, "docs": "/docs"}


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok" if clf else "degraded",
        version=VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        models_loaded=bool(clf),
        classifier_backbone=clf.get("backbone") if clf else None,
        segmenter_loaded=lung_seg is not None,
        threshold_used=clf.get("threshold") if clf else None,
    )


@app.get("/estadisticas", response_model=EstadisticasOut,
         summary="Estadísticas generales para el dashboard")
def estadisticas(
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise HTTPException(400, detail="fecha_desde no puede ser posterior a fecha_hasta.")
    return crud.estadisticas_generales(db, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)


# ── Pacientes ──────────────────────────────────────────────────────────────────

@app.post("/pacientes", response_model=PacienteOut, status_code=201,
          summary="Registrar nuevo paciente")
def crear_paciente(datos: PacienteCreate, db: Session = Depends(get_db)):
    sexo = SexoEnum(datos.sexo) if datos.sexo else None
    tipo = TipoDocumentoEnum(datos.tipo_documento) if datos.tipo_documento else None
    return crud.crear_paciente(
        db,
        nombres=datos.nombres, apellidos=datos.apellidos,
        fecha_nacimiento=datos.fecha_nacimiento, sexo=sexo,
        tipo_documento=tipo, numero_documento=datos.numero_documento,
        telefono=datos.telefono, direccion=datos.direccion,
        contacto_nombre=datos.contacto_nombre,
        contacto_telefono=datos.contacto_telefono,
        contacto_relacion=datos.contacto_relacion,
        notas=datos.notas,
    )


@app.get("/pacientes", response_model=list[PacienteOut],
         summary="Listar pacientes (con búsqueda opcional)")
def listar_pacientes(
    buscar: Optional[str] = Query(None),
    skip:   int = Query(0, ge=0),
    limit:  int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    if buscar:
        return crud.buscar_pacientes(db, buscar, limite=limit)
    return crud.listar_pacientes(db, skip=skip, limit=limit)


@app.get("/pacientes/{paciente_id}", response_model=PacienteDetalle,
         summary="Detalle del paciente con historial de estudios")
def obtener_paciente(paciente_id: int, db: Session = Depends(get_db)):
    paciente = crud.obtener_paciente(db, paciente_id)
    if not paciente:
        raise HTTPException(404, detail=f"Paciente {paciente_id} no encontrado.")
    return paciente


# ── Predicción ─────────────────────────────────────────────────────────────────

@app.post("/predict/{paciente_id}", response_model=PredictResponse,
          summary="Analizar radiografía y guardar resultado en BD")
async def predict(
    paciente_id: int,
    file: UploadFile = File(...),
    fecha_estudio:      Optional[date] = Query(None),
    motivo_consulta:    Optional[str]  = Query(None),
    medico_solicitante: Optional[str]  = Query(None),
    institucion:        Optional[str]  = Query(None),
    db: Session = Depends(get_db),
):
    ts = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()

    if not clf:
        raise HTTPException(503, detail="Modelo no cargado. Revise los logs.")

    paciente = crud.obtener_paciente(db, paciente_id)
    if not paciente:
        raise HTTPException(404, detail=f"Paciente {paciente_id} no encontrado.")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, detail=f"Extensión no permitida: '{suffix}'.")

    content = await file.read()
    if len(content) / (1024*1024) > MAX_FILE_SIZE_MB:
        raise HTTPException(400, detail=f"Archivo muy grande. Máximo {MAX_FILE_SIZE_MB} MB.")
    if len(content) < 1024:
        raise HTTPException(400, detail="Archivo vacío o corrupto.")

    try:
        result = run_inference(content)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except Exception:
        log.error(traceback.format_exc())
        raise HTTPException(500, detail="Error interno durante la inferencia.")

    elapsed_ms = (time.perf_counter() - t0) * 1000
    p          = result["prob_tb"]
    confidence = _confidence(p)
    interp     = _interpretation(result["label"], p)

    w, h = result["image_size_input"]
    estudio = crud.crear_estudio(
        db,
        paciente_id=paciente_id,
        fecha_estudio=fecha_estudio or date.today(),
        nombre_archivo_original=file.filename,
        formato_imagen=suffix.lstrip("."),
        tamanio_bytes=len(content),
        resolucion_px=f"{w}x{h}",
        motivo_consulta=motivo_consulta,
        medico_solicitante=medico_solicitante,
        institucion=institucion,
    )

    img_size = result["image_size_model"]
    resultado = crud.crear_resultado(
        db,
        estudio_id=estudio.id,
        label=result["label"],
        prob_tb=result["prob_tb"],
        prob_normal=result["prob_normal"],
        threshold=result["threshold"],
        nivel_confianza=confidence,
        interpretacion=interp,
        backbone=result["backbone"],
        version_modelo=VERSION,
        enhancement_mode=result["enhancement_mode"],
        segmentacion_usada=result["segmentation_used"],
        resolucion_entrada_modelo=f"{img_size[0]}x{img_size[1]}",
        tiempo_procesamiento_ms=round(elapsed_ms, 1),
    )

    try:
        _save_imagenes_estudio(estudio.id, result)
    except Exception:
        log.error("No se pudieron guardar imágenes del estudio %s: %s",
                  estudio.id, traceback.format_exc())

    log.info(
        f"[PREDICT] paciente={paciente_id} estudio={estudio.id} "
        f"label={result['label']} prob_tb={p:.4f} threshold={clf['threshold']:.4f} "
        f"time={elapsed_ms:.0f}ms"
    )

    public_result = {k: v for k, v in result.items() if not k.startswith("_img_")}

    return PredictResponse(
        **public_result,
        interpretation=interp,
        confidence_level=confidence,
        disclaimer=(
            "Este resultado es generado por un sistema de inteligencia artificial con fines "
            "de apoyo diagnóstico. No constituye un diagnóstico clínico. Debe ser interpretado "
            "por un profesional de salud calificado."
        ),
        estudio_id=estudio.id,
        resultado_id=resultado.id,
        version=VERSION,
        timestamp=ts,
        processing_time_ms=round(elapsed_ms, 1),
    )


# ── Estudios ───────────────────────────────────────────────────────────────────

@app.get("/estudios/{estudio_id}", response_model=EstudioOut,
         summary="Detalle de un estudio con resultado del modelo")
def obtener_estudio(estudio_id: int, db: Session = Depends(get_db)):
    estudio = crud.obtener_estudio(db, estudio_id)
    if not estudio:
        raise HTTPException(404, detail=f"Estudio {estudio_id} no encontrado.")
    return estudio


@app.get("/estudios/{estudio_id}/imagenes", response_model=ImagenesEstudioOut,
         summary="Obtener imágenes generadas durante el procesamiento")
def imagenes_estudio(estudio_id: int, request: Request, db: Session = Depends(get_db)):
    estudio = crud.obtener_estudio(db, estudio_id)
    if not estudio:
        raise HTTPException(404, detail=f"Estudio {estudio_id} no encontrado.")

    folder = STATIC_DIR / str(estudio_id)
    archivos = {
        "original":     folder / "original.jpg",
        "clahe":        folder / "clahe.jpg",
        "segmentacion": folder / "segmentacion.jpg",
        "scorecam":     folder / "scorecam.jpg",
    }
    if not folder.exists() or not all(p.exists() for p in archivos.values()):
        raise HTTPException(404, detail="Imágenes no disponibles para este estudio.")

    base = str(request.base_url).rstrip("/") + f"/static/estudios/{estudio_id}"
    return ImagenesEstudioOut(
        original=f"{base}/original.jpg",
        clahe=f"{base}/clahe.jpg",
        segmentacion=f"{base}/segmentacion.jpg",
        scorecam=f"{base}/scorecam.jpg",
    )
    
@app.get("/estudios", response_model=list[EstudioOut])
def listar_estudios(
    resultado: Optional[str] = Query(None, description="Filtrar por TB o NORMAL"),
    db: Session = Depends(get_db)
):
    estudios = crud.listar_estudios(db, resultado_filtro=resultado)
    return estudios

@app.get("/metrics")
def get_metrics():
    import json
    metrics_path = MODEL_DIR / "densenet_169_tb_best_training_metrics.json"
    with open(metrics_path, "r") as f:
        data = json.load(f)
    return data

# REPORTE
@app.get("/estudios/{estudio_id}/reporte")
def descargar_reporte(estudio_id: int, db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    from database.models import Estudio

    estudio = (
        db.query(Estudio)
        .options(joinedload(Estudio.paciente), joinedload(Estudio.resultado))
        .filter(Estudio.id == estudio_id)
        .first()
    )
    if not estudio:
        raise HTTPException(status_code=404, detail="Estudio no encontrado")

    buffer = generar_reporte_pdf(estudio)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=reporte_estudio_{estudio_id}.pdf"}
    )