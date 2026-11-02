import { TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';

import { DishesService } from '@app/services/dishes/dishes.service';
import { ToastService } from '@app/services/toast/toast.service';
import { DishDetailsPageComponent } from './dish-details-page.component';

describe('DishDetailsPageComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DishDetailsPageComponent],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => 'dish-1' } } },
        },
        {
          provide: DishesService,
          useValue: { getDishById: () => of({ id: 'dish-1' }) },
        },
        {
          provide: ToastService,
          useValue: { success: jasmine.createSpy(), error: jasmine.createSpy() },
        },
      ],
    }).compileComponents();
  });

  it('formats nutrients without duplicating units returned by the API', () => {
    const fixture = TestBed.createComponent(DishDetailsPageComponent);
    const component = fixture.componentInstance;

    expect(component.formatNutritionValue('34 g', 'g')).toBe('34 g');
    expect(component.formatNutritionValue('540 kcal', 'kcal')).toBe('540 kcal');
  });
});
