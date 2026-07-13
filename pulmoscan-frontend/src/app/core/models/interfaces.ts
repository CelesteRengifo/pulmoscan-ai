// src/app/core/models/interfaces.ts

export interface Paciente {
  id: number;
  nombres: string;
  apellidos: string;
  fecha_nacimiento?: string;
  sexo?: 'M' | 'F' | 'O' | 'N';
  tipo_documento?: string;
  numero_documento?: string;
  telefono?: string;
  direccion?: string;
  notas?: string;
  creado_en: string;
}

export interface PacienteCreate {
  nombres: string;
  apellidos: string;
  fecha_nacimiento?: string;
  sexo?: string;
  tipo_documento?: string;
  numero_documento?: string;
  telefono?: string;
}

export interface ImagenesEstudio {
  original: string;
  clahe: string;
  segmentacion: string;
  scorecam: string;
}

export interface ResultadoModelo {
  id: number;
  estudio_id: number;
  label: 'TB' | 'NORMAL';
  prob_tb: number;
  prob_normal: number;
  threshold: number;
  nivel_confianza: 'alta' | 'moderada' | 'baja';
  interpretacion?: string;
  backbone?: string;
  enhancement_mode?: string;
  segmentacion_usada?: boolean;
  resolucion_entrada_modelo?: string;
  tiempo_procesamiento_ms?: number;
  procesado_en: string;
}

export interface Estudio {
  id: number;
  paciente_id: number;
  fecha_estudio: string;
  fecha_carga: string;
  nombre_archivo_original?: string;
  formato_imagen?: string;
  tamanio_bytes?: number;
  resolucion_px?: string;
  motivo_consulta?: string;
  medico_solicitante?: string;
  institucion?: string;
  estado: 'PENDIENTE' | 'PROCESADO' | 'ERROR' | 'REVISADO';
  notas?: string;
  resultado?: ResultadoModelo;
}

export interface PacienteDetalle extends Paciente {
  estudios: Estudio[];
}

export interface PredictResponse {
  label: 'TB' | 'NORMAL';
  prob_tb: number;
  prob_normal: number;
  threshold: number;
  interpretation: string;
  confidence_level: string;
  disclaimer: string;
  backbone: string;
  enhancement_mode: string;
  segmentation_used: boolean;
  image_size_input: number[];
  image_size_model: number[];
  estudio_id: number;
  resultado_id: number;
  version: string;
  timestamp: string;
  processing_time_ms: number;
}

export interface Estadisticas {
  total_pacientes: number;
  total_estudios: number;
  total_tb: number;
  total_normal: number;
  porcentaje_tb: number;
  estudios_pendientes: number;
  estudios_revisados: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
  models_loaded: boolean;
  classifier_backbone?: string;
  segmenter_loaded: boolean;
}
