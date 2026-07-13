import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Detalles } from './detalles';

describe('Detalles', () => {
  let component: Detalles;
  let fixture: ComponentFixture<Detalles>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Detalles],
    }).compileComponents();

    fixture = TestBed.createComponent(Detalles);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
