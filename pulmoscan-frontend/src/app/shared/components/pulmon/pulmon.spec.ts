import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Pulmon } from './pulmon';

describe('Pulmon', () => {
  let component: Pulmon;
  let fixture: ComponentFixture<Pulmon>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Pulmon],
    }).compileComponents();

    fixture = TestBed.createComponent(Pulmon);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
