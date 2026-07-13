import { Component, EventEmitter, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PulmoscanService } from '../../../../core/services/pulmoscan';
import { Paciente, PredictResponse } from '../../../../core/models/interfaces';

@Component({
  selector: 'app-nuevo-diagnostico-modal',
  imports: [CommonModule, FormsModule],
  templateUrl: './nuevo-diagnostico-modal.html',
  styleUrl: './nuevo-diagnostico-modal.scss'
})
export class NuevoDiagnosticoModal {
  private api = inject(PulmoscanService);

  @Output() cerrar = new EventEmitter<void>();
  @Output() resultado = new EventEmitter<{ prediccion: PredictResponse; paciente: Paciente; imagenPreview: string }>();

  paso = signal<1 | 2 | 3>(1);
  buscando = signal(false);
  analizando = signal(false);
  pacienteEncontrado = signal<boolean | null>(null);
  errorMsg = signal('');

  tipoDocumento = 'DNI';
  numeroDocumento = '';

  paciente: Paciente | null = null;
  nombres = '';
  apellidos = '';
  fechaNacimiento = '';
  sexo = '';
  motivoConsulta = '';

  archivoRx: File | null = null;
  previewUrl = signal<string | null>(null);
  arrastrando = signal(false);

  get camposDeshabilitados(): boolean {
    return this.pacienteEncontrado() === true;
  }

  buscarPaciente(): void {
    if (!this.numeroDocumento.trim()) return;
    this.buscando.set(true);
    this.errorMsg.set('');

    this.api.listarPacientes(this.numeroDocumento.trim()).subscribe({
      next: (pacientes) => {
        this.buscando.set(false);
        if (pacientes.length > 0) {
          this.paciente = pacientes[0];
          this.nombres = this.paciente.nombres;
          this.apellidos = this.paciente.apellidos;
          this.fechaNacimiento = this.paciente.fecha_nacimiento ?? '';
          this.sexo = this.paciente.sexo ?? '';
          this.pacienteEncontrado.set(true);
        } else {
          this.paciente = null;
          this.nombres = '';
          this.apellidos = '';
          this.fechaNacimiento = '';
          this.sexo = '';
          this.pacienteEncontrado.set(false);
        }
        this.paso.set(2);
      },
      error: () => {
        this.buscando.set(false);
        this.errorMsg.set('Error al buscar el paciente. Verifica la conexión con el servidor.');
      }
    });
  }

  continuarADatos(): void {
    if (this.pacienteEncontrado()) {
      this.paso.set(3);
      return;
    }
    if (!this.nombres.trim() || !this.apellidos.trim() || !this.fechaNacimiento || !this.sexo) {
      this.errorMsg.set('Completa todos los campos obligatorios.');
      return;
    }
    this.errorMsg.set('');
    this.api.crearPaciente({
      tipo_documento: this.tipoDocumento,
      numero_documento: this.numeroDocumento.trim(),
      nombres: this.nombres.trim(),
      apellidos: this.apellidos.trim(),
      fecha_nacimiento: this.fechaNacimiento,
      sexo: this.sexo
    }).subscribe({
      next: (p) => {
        this.paciente = p;
        this.paso.set(3);
      },
      error: () => this.errorMsg.set('No se pudo registrar el paciente.')
    });
  }

  onDragOver(e: DragEvent): void {
    e.preventDefault();
    this.arrastrando.set(true);
  }

  onDragLeave(): void {
    this.arrastrando.set(false);
  }

  onDrop(e: DragEvent): void {
    e.preventDefault();
    this.arrastrando.set(false);
    const file = e.dataTransfer?.files[0];
    if (file) this.setArchivo(file);
  }

  onFileSelect(e: Event): void {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (file) this.setArchivo(file);
  }

  private setArchivo(file: File): void {
    if (!['image/png', 'image/jpeg'].includes(file.type)) {
      this.errorMsg.set('Solo se admiten imágenes PNG o JPG.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      this.errorMsg.set('La imagen no debe superar los 10 MB.');
      return;
    }
    this.errorMsg.set('');
    this.archivoRx = file;
    const reader = new FileReader();
    reader.onload = () => this.previewUrl.set(reader.result as string);
    reader.readAsDataURL(file);
  }

  quitarArchivo(): void {
    this.archivoRx = null;
    this.previewUrl.set(null);
  }

  analizarRx(): void {
    if (!this.archivoRx || !this.paciente) return;
    this.analizando.set(true);
    this.errorMsg.set('');

    this.api.predict(this.paciente.id, this.archivoRx).subscribe({
      next: (res) => {
        this.analizando.set(false);
        this.resultado.emit({
          prediccion: res,
          paciente: this.paciente!,
          imagenPreview: this.previewUrl()!
        });
      },
      error: () => {
        this.analizando.set(false);
        this.errorMsg.set('Error al analizar la radiografía. Intenta nuevamente.');
      }
    });
  }

  cerrarModal(): void {
    if (this.analizando()) return;
    this.cerrar.emit();
  }

  volverPaso(p: 1 | 2): void {
    this.paso.set(p);
    this.errorMsg.set('');
  }
}