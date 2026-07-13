import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Diagnostico } from './diagnostico';

describe('Diagnostico', () => {
  let component: Diagnostico;
  let fixture: ComponentFixture<Diagnostico>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Diagnostico],
    }).compileComponents();

    fixture = TestBed.createComponent(Diagnostico);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
