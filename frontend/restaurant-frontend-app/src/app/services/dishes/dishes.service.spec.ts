import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { API_BASE_URL } from '@app/shared/config/api-base-url.token';
import { DishState } from '@app/models/enums/dish-state.model';
import { DishType } from '@app/models/enums/dish-type.model';
import { DishesService } from './dishes.service';

describe('DishesService', () => {
  let service: DishesService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: API_BASE_URL, useValue: 'https://test.api' },
      ],
    });
    service = TestBed.inject(DishesService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('loads one dish by its ID', () => {
    service.getDishById('dish/1').subscribe();

    const request = http.expectOne('https://test.api/dishes/dish%2F1');
    expect(request.request.method).toBe('GET');
    request.flush({ id: 'dish/1' });
  });

  it('sends the complete create payload to the dishes endpoint', () => {
    const payload = {
      name: 'Khachapuri',
      description: 'Cheese bread',
      dishType: DishType.MainCourse,
      price: 12,
      weight: '350 g',
      calories: '400',
      proteins: '20',
      fats: '16',
      carbohydrates: '42',
      vitamins: 'Calcium',
      state: DishState.Available,
      locationIds: ['location-1'],
    };

    service.createDish(payload).subscribe();

    const request = http.expectOne('https://test.api/dishes');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(payload);
    request.flush({ id: 'dish-1' });
  });

  it('adds force=true when deleting a dish from every menu', () => {
    service.deleteDish('dish-1', true).subscribe();

    const request = http.expectOne('https://test.api/dishes/dish-1?force=true');
    expect(request.request.method).toBe('DELETE');
    request.flush({});
  });
});
