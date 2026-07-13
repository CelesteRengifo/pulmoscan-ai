import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'diagnostico',
    pathMatch: 'full'
  },
  {
    path: 'diagnostico',
    loadComponent: () =>
      import('./features/diagnostico/diagnostico')
        .then(m => m.Diagnostico)
  },
  {
    path: 'historial',
    loadComponent: () =>
      import('./features/historial/historial')
        .then(m => m.Historial)
  },
  {
    path: 'detalles/:id',
    loadComponent: () =>
      import('./features/detalles/detalles')
        .then(m => m.Detalles)
  },
  {
    path: 'acerca-de',
    loadComponent: () =>
      import('./features/acerca-de/acerca-de')
        .then(m => m.AcercaDe)
  },
  {
    path: '**',
    redirectTo: 'diagnostico'
  }
];