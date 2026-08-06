import { ApiService } from '../services/api';
import { mockApiService } from '../services/mock-api';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CentersComponent } from './centers';

describe('CentersComponent', () => {
  let component: CentersComponent;
  let fixture: ComponentFixture<CentersComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CentersComponent],
      providers: [provideHttpClient(), provideRouter([]), { provide: ApiService, useValue: mockApiService }],
    }).compileComponents();

    fixture = TestBed.createComponent(CentersComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
