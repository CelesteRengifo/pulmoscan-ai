import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { NavbarComponent } from '../../shared/components/navbar/navbar';
import { environment } from '../../../environments/environment';

export interface EstudioResumen {
  id: number;
  paciente_id: number;
  fecha_carga: string;
  nombre_archivo_original: string;
  resultado?: {
    label: string;
    prob_tb: number;
    nivel_confianza: string;
    tiempo_procesamiento_ms: number;
  };
}

interface PacienteCache {
  [id: number]: string;
}

@Component({
  selector: 'app-historial',
  imports: [NavbarComponent],
  templateUrl: './historial.html',
  styleUrl: './historial.scss'
})
export class Historial implements OnInit {
  private http = inject(HttpClient);
  private router = inject(Router);

  estudios = signal<EstudioResumen[]>([]);
  cargando = signal(true);
  error = signal<string | null>(null);
  filtro = signal<'TODOS' | 'TB' | 'NORMAL'>('TODOS');
  seleccionadoId = signal<number | null>(null);
  menuAbiertoId = signal<number | null>(null);
  imagenPreviewUrl = signal<string | null>(null);
  cargandoImagen = signal(false);
  pacientesCache = signal<PacienteCache>({});

  estudiosFiltered = computed(() => {
    const f = this.filtro();
    const lista = this.estudios();
    if (f === 'TODOS') return lista;
    return lista.filter(e => e.resultado?.label === f);
  });

  ngOnInit(): void {
    this.cargarEstudios();
  }

  cargarEstudios(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.http.get<EstudioResumen[]>(`${environment.apiUrl}/estudios`)
      .subscribe({
        next: data => {
          this.estudios.set(data);
          this.cargando.set(false);
          this.cargarPacientes(data);
        },
        error: () => {
          this.error.set('No se pudo cargar el historial.');
          this.cargando.set(false);
        }
      });
  }

  cargarPacientes(estudios: EstudioResumen[]): void {
    const ids = [...new Set(estudios.map(e => e.paciente_id))];
    ids.forEach(id => {
      this.http.get<any>(`${environment.apiUrl}/pacientes/${id}`)
        .subscribe({
          next: p => {
            this.pacientesCache.update(cache => ({
              ...cache,
              [id]: `${p.nombres} ${p.apellidos}`
            }));
          }
        });
    });
  }

  toggleOjo(estudio: EstudioResumen, event: Event): void {
    event.stopPropagation();
    const mismo = this.seleccionadoId() === estudio.id;
    if (mismo) {
      this.seleccionadoId.set(null);
      this.imagenPreviewUrl.set(null);
      return;
    }
    this.seleccionadoId.set(estudio.id);
    this.menuAbiertoId.set(null);
    this.cargandoImagen.set(true);
    this.imagenPreviewUrl.set(null);
    this.http.get<any>(`${environment.apiUrl}/estudios/${estudio.id}/imagenes`)
      .subscribe({
        next: imgs => {
          this.imagenPreviewUrl.set(imgs.original ?? null);
          this.cargandoImagen.set(false);
        },
        error: () => { this.cargandoImagen.set(false); }
      });
  }

  toggleMenu(id: number, event: Event): void {
    event.stopPropagation();
    this.menuAbiertoId.set(this.menuAbiertoId() === id ? null : id);
  }

  cerrarMenu(): void {
    this.menuAbiertoId.set(null);
  }

  irADetalles(id: number, event: Event): void {
    event.stopPropagation();
    this.menuAbiertoId.set(null);
    this.router.navigate(['/detalles', id]);
  }

  eliminar(id: number, event: Event): void {
    event.stopPropagation();
    this.menuAbiertoId.set(null);
    if (!confirm('¿Eliminar este estudio del historial?')) return;
    this.http.delete(`${environment.apiUrl}/estudios/${id}`)
      .subscribe({
        next: () => {
          this.estudios.update(lista => lista.filter(e => e.id !== id));
          if (this.seleccionadoId() === id) {
            this.seleccionadoId.set(null);
            this.imagenPreviewUrl.set(null);
          }
        },
        error: () => alert('No se pudo eliminar el estudio.')
      });
  }

  descargarPDF(id: number, event: Event): void {
    event.stopPropagation();
    this.menuAbiertoId.set(null);
    window.open(`${environment.apiUrl}/estudios/${id}/reporte`, '_blank');
  }

  formatFecha(iso: string): string {
    if (!iso) return '—';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '—';
    return d.toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  formatHora(iso: string): string {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
  }

  probPorcentaje(prob: number): number {
    return Math.round(prob * 100);
  }

  nombrePaciente(e: EstudioResumen): string {
    return this.pacientesCache()[e.paciente_id] ?? '...';
  }

  inicialPaciente(e: EstudioResumen): string {
    const nombre = this.pacientesCache()[e.paciente_id];
    return nombre ? nombre.charAt(0).toUpperCase() : '?';
  }
  
}