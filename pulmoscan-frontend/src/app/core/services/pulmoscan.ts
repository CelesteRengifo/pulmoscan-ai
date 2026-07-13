// src/app/core/services/pulmoscan.service.ts

import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  Paciente,
  PacienteCreate,
  PacienteDetalle,
  Estudio,
  PredictResponse,
  Estadisticas,
  HealthResponse,
  ImagenesEstudio,
} from '../models/interfaces';

@Injectable({
  providedIn: 'root',
})
export class PulmoscanService {
  private readonly API = 'http://127.0.0.1:8000';

  constructor(private http: HttpClient) {}

  // ── Health ──────────────────────────────────────────────
  health(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>(`${this.API}/health`);
  }

  // ── Estadísticas ────────────────────────────────────────
  estadisticas(): Observable<Estadisticas> {
    return this.http.get<Estadisticas>(`${this.API}/estadisticas`);
  }

  // ── Pacientes ───────────────────────────────────────────
  crearPaciente(datos: PacienteCreate): Observable<Paciente> {
    return this.http.post<Paciente>(`${this.API}/pacientes`, datos);
  }

  listarPacientes(buscar?: string): Observable<Paciente[]> {
    let params = new HttpParams();
    if (buscar) params = params.set('buscar', buscar);
    return this.http.get<Paciente[]>(`${this.API}/pacientes`, { params });
  }

  obtenerPaciente(id: number): Observable<PacienteDetalle> {
    return this.http.get<PacienteDetalle>(`${this.API}/pacientes/${id}`);
  }

  obtenerImagenesEstudio(id: number): Observable<ImagenesEstudio> {
    return this.http.get<ImagenesEstudio>(`${this.API}/estudios/${id}/imagenes`);
  }

  // ── Predict ─────────────────────────────────────────────
  predict(pacienteId: number, file: File): Observable<PredictResponse> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<PredictResponse>(
      `${this.API}/predict/${pacienteId}`,
      form
    );
  }

  // ── Estudios ────────────────────────────────────────────
  obtenerEstudio(id: number): Observable<Estudio> {
    return this.http.get<Estudio>(`${this.API}/estudios/${id}`);
  }
  
}