import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { DishListResponse } from '@app/models/dishes/dish-list-response.model';
import { Order } from '@app/models/orders/order.model';
import { API_BASE_URL } from '@app/shared/config/api-base-url.token';

import { PreOrdersService } from './pre-orders.service';

describe('PreOrdersService', () => {
  let service: PreOrdersService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: API_BASE_URL, useValue: 'https://test.api' },
      ],
    });

    service = TestBed.inject(PreOrdersService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('shares an in-flight request and reuses recently loaded orders', () => {
    const firstResults: unknown[] = [];
    const secondResults: unknown[] = [];

    service.getPreOrders().subscribe((orders) => firstResults.push(orders));
    service.getPreOrders().subscribe((orders) => secondResults.push(orders));

    const request = httpMock.expectOne('https://test.api/orders');
    request.flush([]);

    service.getPreOrders().subscribe((orders) => firstResults.push(orders));

    expect(firstResults).toEqual([[], []]);
    expect(secondResults).toEqual([[]]);
    httpMock.expectNone('https://test.api/orders');
  });

  it('serializes concurrent dish additions for the same reservation', () => {
    const dish1: DishListResponse = {
      id: 'dish-1',
      name: 'Dish 1',
      imageUrl: '',
      price: 10,
      state: '',
      weight: '',
      dishType: '',
      description: '',
      calories: '',
      proteins: '',
      carbohydrates: '',
      fats: '',
      vitamins: '',
    };
    const dish2: DishListResponse = {
      ...dish1,
      id: 'dish-2',
      name: 'Dish 2',
    };
    const reservationId = 'reservation-1';

    service.addDishToPreOrderByReservationId(reservationId, dish1, 1).subscribe();
    service.addDishToPreOrderByReservationId(reservationId, dish2, 1).subscribe();

    httpMock.expectOne('https://test.api/orders').flush([]);

    const createRequest = httpMock.expectOne('https://test.api/orders');
    expect(createRequest.request.method).toBe('POST');
    expect(createRequest.request.body).toEqual({
      reservationId,
      orderItems: [{ dishId: 'dish-1', quantity: 1 }],
    });
    createRequest.flush({
      orderId: 'order-1',
      reservationId,
      orderItems: [{ dish: dish1, quantity: 1, state: 0 }],
    } as Order);

    const refreshRequest = httpMock.expectOne('https://test.api/orders');
    expect(refreshRequest.request.method).toBe('GET');
    refreshRequest.flush([
      {
        orderId: 'order-1',
        reservationId,
        orderItems: [{ dish: dish1, quantity: 1, state: 0 }],
      },
    ] as Order[]);

    const updateRequest = httpMock.expectOne(`https://test.api/orders/${reservationId}`);
    expect(updateRequest.request.method).toBe('PUT');
    expect(updateRequest.request.body).toEqual({
      orderItems: [
        { dishId: 'dish-1', quantity: 1 },
        { dishId: 'dish-2', quantity: 1 },
      ],
    });
    updateRequest.flush({});
    httpMock.expectNone((request) => request.method === 'POST');
  });
});
