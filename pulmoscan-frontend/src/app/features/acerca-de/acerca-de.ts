import { Component, signal, inject, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { NavbarComponent } from '../../shared/components/navbar/navbar';
import { environment } from '../../../environments/environment';

interface Metricas {
  threshold: number;
  threshold_rule: string;
  enhancement_mode: string;
  lung_segmentation_mode: string;
  backbone: string;
  best_epoch: number;
  best_monitor_score: number;
  test_1: {
    auc: number;
    f1: number;
    precision: number;
    sensitivity: number;
    specificity: number;
    balanced_accuracy: number;
    tn: number;
    fp: number;
    fn: number;
    tp: number;
  };
}

const PIPELINE_PASOS = [
  {
    icono: 'rx',
    titulo: 'Imagen RX',
    subtitulo: 'Entrada',
    descripcion: 'Se recibe la radiografía de tórax en formato JPEG o PNG. La imagen puede provenir de distintos equipos radiológicos y resoluciones.'
  },
  {
    icono: 'clahe',
    titulo: 'Preprocesado',
    subtitulo: 'CLAHE + gamma',
    descripcion: 'Se aplica CLAHE (Contrast Limited Adaptive Histogram Equalization) seguido de corrección gamma para mejorar el contraste local de la imagen y resaltar estructuras pulmonares.'
  },
  {
    icono: 'unet',
    titulo: 'Segmentación',
    subtitulo: 'Attention U-Net',
    descripcion: 'Una red Attention U-Net segmenta la región pulmonar, aislando los pulmones del resto de la imagen para reducir el ruido de fondo y enfocar el análisis.'
  },
  {
    icono: 'densenet',
    titulo: 'Clasificación',
    subtitulo: 'DenseNet169',
    descripcion: 'El modelo DenseNet169 preentrenado y ajustado fino clasifica la imagen segmentada como TB positivo o negativo, generando una probabilidad de tuberculosis.'
  },
  {
    icono: 'cam',
    titulo: 'Explicabilidad',
    subtitulo: 'Score-CAM',
    descripcion: 'Score-CAM genera un mapa de activación que resalta las regiones de la radiografía que más influyeron en la decisión del modelo, facilitando la interpretación clínica.'
  },
  {
    icono: 'diag',
    titulo: 'Diagnóstico',
    subtitulo: 'Resultado',
    descripcion: 'Se presenta el resultado final con la clasificación (TB+ / Normal), probabilidad, nivel de confianza y el mapa de calor Score-CAM para apoyo al diagnóstico.'
  }
];

const EQUIPO = [
  { iniciales: 'AC', nombre: 'Anny Celeste', apellido: 'Alva Rengifo' },
  { iniciales: 'JC', nombre: 'Jeysson Rafael', apellido: 'Cobeñas Gonzales' },
  { iniciales: 'LX', nombre: 'Li', apellido: 'Xuan' },
  { iniciales: 'JS', nombre: 'Jose Diego', apellido: 'Soto Arevalo' },
  { iniciales: 'FM', nombre: 'Fabrizio Gael', apellido: 'Mozombite Gaston' },
];

const DATASETS = [
  { nombre: 'Montgomery County', detalle: '138 imágenes · 58 TB · 80 normales' },
  { nombre: 'Shenzhen', detalle: '662 imágenes · 336 TB · 326 normales' },
  { nombre: 'TBX11K Simplified', detalle: '5,060 imágenes seleccionadas' },
];

@Component({
  selector: 'app-acerca-de',
  imports: [NavbarComponent],
  templateUrl: './acerca-de.html',
  styleUrl: './acerca-de.scss'
})
export class AcercaDe implements OnInit {
  private http = inject(HttpClient);

  metricas = signal<Metricas | null>(null);
  cargando = signal(true);
  pasoActivo = signal(0);

  pipeline = PIPELINE_PASOS;
  equipo = EQUIPO;
  datasets = DATASETS;

  ngOnInit(): void {
    this.http.get<Metricas>(`${environment.apiUrl}/metrics`)
      .subscribe({
        next: data => {
          this.metricas.set(data);
          this.cargando.set(false);
        },
        error: () => this.cargando.set(false)
      });
  }

  pct(val: number): string {
    return (val * 100).toFixed(1) + '%';
  }

  fmt(val: number, dec = 4): string {
    return val.toFixed(dec);
  }
}
