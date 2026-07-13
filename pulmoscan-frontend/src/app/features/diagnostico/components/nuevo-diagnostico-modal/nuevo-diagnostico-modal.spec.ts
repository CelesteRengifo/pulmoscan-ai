import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NuevoDiagnosticoModal } from './nuevo-diagnostico-modal';

describe('NuevoDiagnosticoModal', () => {
  let component: NuevoDiagnosticoModal;
  let fixture: ComponentFixture<NuevoDiagnosticoModal>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NuevoDiagnosticoModal],
    }).compileComponents();

    fixture = TestBed.createComponent(NuevoDiagnosticoModal);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
