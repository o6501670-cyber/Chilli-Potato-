import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Centers } from './centers';

describe('Centers', () => {
  let component: Centers;
  let fixture: ComponentFixture<Centers>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Centers],
    }).compileComponents();

    fixture = TestBed.createComponent(Centers);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
