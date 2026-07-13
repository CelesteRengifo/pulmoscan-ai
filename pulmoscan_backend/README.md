# PulmoScan AI — Backend

API de detección automatizada de tuberculosis pulmonar mediante análisis de radiografías de tórax con DenseNet169.

## Requisitos
- Python 3.10
- PostgreSQL
- Los modelos .pt (ver más abajo)

## Instalación

1. Clona el repositorio:
   git clone https://github.com/CelesteRengifo/pulmoscan-ai.git
   cd pulmoscan-ai/pulmoscan_backend

2. Instala dependencias:
   pip install -r requirements.txt

3. Configura las variables de entorno:
   - Copia .env.example a .env
   - Rellena con tus credenciales de PostgreSQL

4. Descarga los modelos y colócalos en la carpeta models/:
   https://drive.google.com/drive/folders/1t7I8jWKb2lZu3hEdNXc8GS_H4yCpP_PH?usp=sharing

   Archivos necesarios:
   - densenet_169_tb_best.pt
   - lung_attention_unet_best.pt

5. Ejecuta el servidor:
   python -m uvicorn main:app --reload

## Endpoints principales
- POST /predict/{paciente_id} — Analiza una radiografía
- GET  /estudios — Lista todos los estudios
- GET  /estudios/{id}/reporte — Descarga reporte PDF
- GET  /metrics — Métricas del modelo
- GET  /pacientes — Lista pacientes
