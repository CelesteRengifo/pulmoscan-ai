import { Component, signal, inject, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { NavbarComponent } from '../../shared/components/navbar/navbar';
import { PulmonComponent } from '../../shared/components/pulmon/pulmon';
import { NuevoDiagnosticoModal } from './components/nuevo-diagnostico-modal/nuevo-diagnostico-modal';
import { Paciente, PredictResponse } from '../../core/models/interfaces';
import { environment } from '../../../environments/environment';

interface DiagnosticoGuardado {
  prediccion: PredictResponse;
  paciente: Paciente;
  imagenPreview: string;
}

@Component({
  selector: 'app-diagnostico',
  imports: [
    NavbarComponent,
    PulmonComponent,
    NuevoDiagnosticoModal
  ],
  templateUrl: './diagnostico.html',
  styleUrl: './diagnostico.scss'
})
export class Diagnostico implements OnInit {
  private router = inject(Router);

  private readonly storageKey = 'diagnostico_actual';

  mostrarModal = signal(false);
  paciente = signal<Paciente | null>(null);
  prediccion = signal<PredictResponse | null>(null);
  imagenPreview = signal<string | null>(null);

  ngOnInit(): void {
    this.recuperarDiagnostico();
  }

  get estadoPulmon(): 'neutro' | 'tb' | 'normal' {
    const prediccion = this.prediccion();

    if (!prediccion) {
      return 'neutro';
    }

    return prediccion.label === 'TB' ? 'tb' : 'normal';
  }

  get probabilidadTB(): number {
    return Math.round((this.prediccion()?.prob_tb ?? 0) * 100);
  }

  get iniciales(): string {
    const paciente = this.paciente();

    if (!paciente) {
      return '';
    }

    const nombre = (paciente.nombres ?? '').trim().charAt(0);
    const apellido = (paciente.apellidos ?? '').trim().charAt(0);

    return `${nombre}${apellido}`.toUpperCase();
  }

  get edad(): string {
    const paciente = this.paciente();

    if (!paciente?.fecha_nacimiento) {
      return '—';
    }

    const nacimiento = this.crearFechaLocal(paciente.fecha_nacimiento);

    if (isNaN(nacimiento.getTime())) {
      return '—';
    }

    const hoy = new Date();

    let años = hoy.getFullYear() - nacimiento.getFullYear();

    const diferenciaMeses = hoy.getMonth() - nacimiento.getMonth();

    if (
      diferenciaMeses < 0 ||
      (
        diferenciaMeses === 0 &&
        hoy.getDate() < nacimiento.getDate()
      )
    ) {
      años--;
    }

    return años >= 0 ? `${años} años` : '—';
  }

  get fechaNacimientoFmt(): string {
    const paciente = this.paciente();

    if (!paciente?.fecha_nacimiento) {
      return '—';
    }

    const fecha = this.crearFechaLocal(paciente.fecha_nacimiento);

    if (isNaN(fecha.getTime())) {
      return paciente.fecha_nacimiento;
    }

    const dia = String(fecha.getDate()).padStart(2, '0');
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');

    return `${dia}/${mes}/${fecha.getFullYear()}`;
  }

  get indicacion(): string {
    const prediccion = this.prediccion();

    if (!prediccion) {
      return '';
    }

    return prediccion.label === 'TB'
      ? 'Se detectaron patrones compatibles con tuberculosis pulmonar. Se recomienda confirmación microbiológica.'
      : 'No se detectaron patrones sugestivos de tuberculosis. Continúe con seguimiento clínico habitual.';
  }

  onResultado(data: DiagnosticoGuardado): void {
    this.prediccion.set(data.prediccion);
    this.paciente.set(data.paciente);
    this.imagenPreview.set(data.imagenPreview);
    this.mostrarModal.set(false);

    this.guardarDiagnostico(data);
  }

  irADetalles(): void {
    const prediccion = this.prediccion();

    if (!prediccion) {
      return;
    }

    this.router.navigate(['/detalles', prediccion.estudio_id]);
  }

  limpiarDiagnostico(): void {
    this.prediccion.set(null);
    this.paciente.set(null);
    this.imagenPreview.set(null);

    sessionStorage.removeItem(this.storageKey);
  }

  private guardarDiagnostico(data: DiagnosticoGuardado): void {
    try {
      sessionStorage.setItem(
        this.storageKey,
        JSON.stringify(data)
      );
    } catch (error) {
      console.error('No se pudo guardar el diagnóstico:', error);
    }
  }

  private recuperarDiagnostico(): void {
    try {
      const diagnosticoGuardado = sessionStorage.getItem(this.storageKey);

      if (!diagnosticoGuardado) {
        return;
      }

      const data = JSON.parse(
        diagnosticoGuardado
      ) as DiagnosticoGuardado;

      if (!data.prediccion || !data.paciente) {
        sessionStorage.removeItem(this.storageKey);
        return;
      }

      this.prediccion.set(data.prediccion);
      this.paciente.set(data.paciente);
      this.imagenPreview.set(data.imagenPreview ?? null);
    } catch (error) {
      console.error('No se pudo recuperar el diagnóstico:', error);
      sessionStorage.removeItem(this.storageKey);
    }
  }

  private crearFechaLocal(fecha: string): Date {
    const fechaSinHora = fecha.split('T')[0];
    const partes = fechaSinHora.split('-').map(Number);

    if (partes.length !== 3) {
      return new Date(fecha);
    }

    const [año, mes, dia] = partes;

    return new Date(año, mes - 1, dia);
  }

  descargarReporte(): void {
    const prediccion = this.prediccion();
    if (!prediccion) return;
    window.open(`${environment.apiUrl}/estudios/${prediccion.estudio_id}/reporte`, '_blank');
  }
}
