# PulmoScan AI — Backend

API REST construida con **FastAPI** para la detección de Tuberculosis Pulmonar
a partir de radiografías de tórax (CXR).

> ⚠️ **Solo para uso como prototipo de apoyo diagnóstico.**
> No reemplaza el criterio clínico especializado.

---

## Estructura esperada

```
pulmoscan_backend/
├── main.py
├── requirements.txt
├── Dockerfile
└── models/
    ├── densenet_169_tb_best.pt
    └── lung_attention_unet_best.pt
```

---

## Ejecución local

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Colocar los modelos en models/
mkdir models
# copiar densenet_169_tb_best.pt y lung_attention_unet_best.pt aquí

# 3. Levantar el servidor
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Documentación interactiva disponible en: http://localhost:8000/docs

---

## Ejecución con Docker

```bash
# Construir imagen
docker build -t pulmoscan-backend .

# Ejecutar montando la carpeta de modelos
docker run -p 8000:8000 \
  -v $(pwd)/models:/app/models \
  pulmoscan-backend
```

---

## Endpoints

### `GET /health`
Estado del servicio y verificación de modelos cargados.

```json
{
  "status": "ok",
  "version": "1.0.0-demo",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "models_loaded": true,
  "classifier_backbone": "densenet169",
  "segmenter_loaded": true
}
```

### `POST /predict`
Analiza una radiografía de tórax.

**Request:** `multipart/form-data`
- `file`: imagen JPG, PNG, BMP o TIFF (máximo 10 MB)

**Response:**
```json
{
  "label": "TB",
  "prob_tb": 0.7520,
  "prob_normal": 0.2480,
  "threshold": 0.44,
  "interpretation": "La radiografía presenta hallazgos compatibles con tuberculosis pulmonar (probabilidad 75.2%)...",
  "confidence_level": "moderada",
  "disclaimer": "Este resultado es generado por un sistema de IA con fines de apoyo diagnóstico...",
  "backbone": "densenet169",
  "enhancement_mode": "clahe_gamma",
  "segmentation_used": true,
  "image_size_input": [1024, 1024],
  "image_size_model": [380, 380],
  "version": "1.0.0-demo",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "processing_time_ms": 1234.5
}
```

---

## Configuración para Angular

En el servicio Angular, apuntar a:
```
http://localhost:8000/predict   (desarrollo)
http://<servidor>:8000/predict  (producción)
```

El CORS está habilitado para todos los orígenes en modo prototipo.
En producción, reemplazar `allow_origins=["*"]` por el dominio Angular específico.

---

## Validaciones implementadas

| Validación | Detalle |
|---|---|
| Extensión de archivo | `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tif`, `.tiff` |
| Tamaño máximo | 10 MB |
| Tamaño mínimo de imagen | 64×64 px |
| Tamaño máximo de imagen | 6000×6000 px |
| Archivo vacío o corrupto | Verificación de tamaño mínimo en bytes |
| Modelos no cargados | HTTP 503 con mensaje claro |
