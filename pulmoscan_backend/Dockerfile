FROM python:3.11-slim

LABEL maintainer="PulmoScan AI"
LABEL description="Backend de detección de TB pulmonar - Solo prototipo de apoyo diagnóstico"

# Dependencias del sistema para OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY main.py .

# Los modelos se montan como volumen externo (no se incluyen en la imagen)
# Estructura esperada en ejecución:
#   /app/models/densenet_169_tb_best.pt
#   /app/models/lung_attention_unet_best.pt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
