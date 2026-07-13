import { Component, inject, OnInit, signal } from '@angular/core';
import { DatePipe, TitleCasePipe } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin } from 'rxjs';
import { Location } from '@angular/common';

import { NavbarComponent } from '../../shared/components/navbar/navbar';
import { PulmoscanService } from '../../core/services/pulmoscan';
import {
  Estudio,
  ImagenesEstudio
} from '../../core/models/interfaces';

@Component({
  selector: 'app-detalles',
  standalone: true,
  imports: [
    NavbarComponent,
    TitleCasePipe,
    DatePipe
  ],
  templateUrl: './detalles.html',
  styleUrl: './detalles.scss'
})
export class Detalles implements OnInit {

  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(PulmoscanService);
  private location = inject(Location);
  readonly estudio = signal<Estudio | null>(null);
  readonly imagenes = signal<ImagenesEstudio | null>(null);
  readonly cargando = signal<boolean>(true);
  readonly error = signal<string>('');

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    const id = Number(idParam);

    if (!idParam || Number.isNaN(id) || id <= 0) {
      this.error.set('El identificador del estudio no es válido.');
      this.cargando.set(false);
      return;
    }

    forkJoin({
      estudio: this.api.obtenerEstudio(id),
      imagenes: this.api.obtenerImagenesEstudio(id)
    }).subscribe({
      next: ({ estudio, imagenes }) => {
        this.estudio.set(estudio);
        this.imagenes.set(imagenes);
        this.cargando.set(false);
      },
      error: (error) => {
        console.error('Error al cargar el detalle del estudio:', error);

        this.error.set(
          'No se pudo cargar la información del estudio.'
        );

        this.cargando.set(false);
      }
    });
  }

  get resultado() {
    return this.estudio()?.resultado ?? null;
  }

  get probabilidadTB(): number {
    return Math.round(
      (this.resultado?.prob_tb ?? 0) * 100
    );
  }

  get probabilidadNormal(): number {
    return Math.round(
      (this.resultado?.prob_normal ?? 0) * 100
    );
  }

  volver(): void {
    this.location.back();
  }
}