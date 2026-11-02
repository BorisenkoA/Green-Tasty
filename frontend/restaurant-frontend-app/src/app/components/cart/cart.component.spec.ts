import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of, Subject } from 'rxjs';

import { Order } from '@app/models/orders/order.model';
import { Reservation, ReservationStatus } from '@app/models/reservations/reservation.model';
import { PreOrdersService } from '@app/services/pre-orders/pre-orders.service';
import { ReservationService } from '@app/services/reservation/reservation.service';

import { CartComponent } from './cart.component';

describe('CartComponent', () => {
  let component: CartComponent;
  let fixture: ComponentFixture<CartComponent>;

  let preOrdersServiceMock: jasmine.SpyObj<PreOrdersService>;
  let reservationServiceMock: jasmine.SpyObj<ReservationService>;
  let routerMock: jasmine.SpyObj<Router>;

  beforeEach(async () => {
    preOrdersServiceMock = jasmine.createSpyObj<PreOrdersService>('PreOrdersService', [
      'getPreOrders',
      'cancelPreOrderByReservationId',
      'unsubmitPreOrderByReservationId',
      'submitPreOrderByReservationId',
      'editPreOrderByReservationId',
    ]);

    routerMock = jasmine.createSpyObj<Router>('Router', ['navigate']);

    preOrdersServiceMock.getPreOrders.and.returnValue(of([]));
    reservationServiceMock = jasmine.createSpyObj<ReservationService>('ReservationService', [
      'getReservationsForUser$',
    ]);
    reservationServiceMock.getReservationsForUser$.and.returnValue(of([]));

    await TestBed.configureTestingModule({
      imports: [CartComponent],
      providers: [
        {
          provide: PreOrdersService,
          useValue: preOrdersServiceMock,
        },
        {
          provide: Router,
          useValue: routerMock,
        },
        {
          provide: ReservationService,
          useValue: reservationServiceMock,
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CartComponent);
    component = fixture.componentInstance;

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show the empty cart immediately while orders are loading', () => {
    const ordersResponse = new Subject<Order[]>();
    preOrdersServiceMock.getPreOrders.and.returnValue(ordersResponse);
    reservationServiceMock.getReservationsForUser$.and.returnValue(
      of([
        {
          id: 'reservation-1',
          status: ReservationStatus.Reserved,
        },
      ] as Reservation[])
    );

    const pendingFixture = TestBed.createComponent(CartComponent);
    pendingFixture.detectChanges();

    expect(pendingFixture.nativeElement.textContent).toContain('Your cart is empty');
    expect(pendingFixture.nativeElement.textContent).not.toContain('Loading your cart');

    ordersResponse.next([
      {
        orderId: 'order-1',
        status: 0,
        reservationId: 'reservation-1',
        reservationAddress: 'Test restaurant',
        reservationTime: '2026-10-31T12:00:00Z',
        orderItems: [
          {
            quantity: 1,
            state: 0,
            dish: {
              id: 'dish-1',
              name: 'Loaded dish',
              price: 10,
              imageUrl: 'assets/img/dish.png',
            },
          },
        ],
      },
    ] as Order[]);
    ordersResponse.complete();
    pendingFixture.detectChanges();

    expect(pendingFixture.nativeElement.textContent).toContain('Loaded dish');
    pendingFixture.destroy();
  });

  it('should exclude orders for cancelled or missing reservations', () => {
    component.orders.set([
      {
        orderId: 'active-order',
        status: 0,
        reservationId: 'active-reservation',
        reservationAddress: 'Test restaurant',
        reservationTime: '2026-10-31T12:00:00Z',
        orderItems: [],
      },
      {
        orderId: 'cancelled-order',
        status: 0,
        reservationId: 'cancelled-reservation',
        reservationAddress: 'Test restaurant',
        reservationTime: '2026-10-31T12:00:00Z',
        orderItems: [],
      },
      {
        orderId: 'orphaned-order',
        status: 0,
        reservationId: 'missing-reservation',
        reservationAddress: 'Test restaurant',
        reservationTime: '2026-10-31T12:00:00Z',
        orderItems: [],
      },
      {
        orderId: 'finished-order',
        status: 1,
        reservationId: 'finished-reservation',
        reservationAddress: 'Test restaurant',
        reservationTime: '2026-10-31T12:00:00Z',
        orderItems: [],
      },
    ] as Order[]);
    reservationServiceMock.getReservationsForUser$.and.returnValue(
      of([
        {
          id: 'active-reservation',
          status: ReservationStatus.Reserved,
        },
        {
          id: 'cancelled-reservation',
          status: ReservationStatus.Cancelled,
        },
        {
          id: 'finished-reservation',
          status: ReservationStatus.Finished,
        },
      ] as Reservation[])
    );
    preOrdersServiceMock.getPreOrders.and.returnValue(of(component.orders()));

    const filteredFixture = TestBed.createComponent(CartComponent);
    filteredFixture.detectChanges();

    expect(filteredFixture.componentInstance.orders().map((order) => order.orderId)).toEqual([
      'active-order',
      'finished-order',
    ]);
    filteredFixture.destroy();
  });

  it('should emit closeCartEvent when closeCart is called', () => {
    spyOn(component.closeCartEvent, 'emit');

    component.closeCart();

    expect(component.closeCartEvent.emit).toHaveBeenCalled();
  });

  it('should return submitted orders with statuses 1 and 3', () => {
    component.orders.set([
      {
        orderId: 'order-1',
        status: 1,
      },
      {
        orderId: 'order-2',
        status: 2,
      },
      {
        orderId: 'order-3',
        status: 3,
      },
      {
        orderId: 'order-4',
        status: 0,
      },
    ] as Order[]);

    expect(component.submittedOrders().map((order) => order.status)).toEqual([1, 3]);
  });

  it('should return unsubmitted orders with status 0', () => {
    component.orders.set([
      {
        orderId: 'order-1',
        status: 0,
      },
      {
        orderId: 'order-2',
        status: 1,
      },
      {
        orderId: 'order-3',
        status: 3,
      },
    ] as Order[]);

    expect(component.unsubmittedOrders().map((order) => order.status)).toEqual([0]);
  });

  it('should navigate to reservations when goToReservations is called', () => {
    component.goToReservations();

    expect(routerMock.navigate).toHaveBeenCalledWith(['/reservations']);
  });

  it('should open the menu for the selected reservation to add a dish', () => {
    component.orders.set([
      {
        orderId: 'order-1',
        status: 0,
        reservationId: 'reservation-1',
        reservationAddress: 'Test restaurant',
        reservationTime: '2026-10-31T12:00:00Z',
        orderItems: [],
      },
    ] as Order[]);
    spyOn(component.closeCartEvent, 'emit');

    component.addDishToOrder('order-1');

    expect(component.closeCartEvent.emit).toHaveBeenCalled();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/menu'], {
      queryParams: {
        preOrder: true,
        reservationId: 'reservation-1',
        reservationLabel: 'Test restaurant',
      },
    });
  });

  it('should update quantity immediately and debounce the API update', fakeAsync(() => {
    const order = {
      orderId: 'order-1',
      status: 0,
      reservationId: 'reservation-1',
      orderItems: [
        {
          quantity: 2,
          state: 0,
          dish: { id: 'dish-1', price: 10 },
        },
      ],
    } as Order;
    component.orders.set([order]);
    preOrdersServiceMock.editPreOrderByReservationId.and.returnValue(of({}));

    component.updateDishQuantity('order-1', 'dish-1', 3);
    component.updateDishQuantity('order-1', 'dish-1', 4);

    expect(component.orders()[0].orderItems[0].quantity).toBe(4);
    expect(preOrdersServiceMock.editPreOrderByReservationId).not.toHaveBeenCalled();
    expect(preOrdersServiceMock.editPreOrderByReservationId).not.toHaveBeenCalled();

    tick(199);
    expect(preOrdersServiceMock.editPreOrderByReservationId).not.toHaveBeenCalled();

    tick(1);

    expect(preOrdersServiceMock.editPreOrderByReservationId).toHaveBeenCalledTimes(1);
    expect(
      preOrdersServiceMock.editPreOrderByReservationId.calls.mostRecent().args[1].orderItems[0]
        .quantity
    ).toBe(4);
    expect(preOrdersServiceMock.getPreOrders).toHaveBeenCalledTimes(1);
  }));

  it('should remove a dish immediately and debounce the API update', fakeAsync(() => {
    const order = {
      orderId: 'order-1',
      status: 0,
      reservationId: 'reservation-1',
      orderItems: [
        {
          quantity: 1,
          state: 0,
          dish: { id: 'dish-1', price: 10 },
        },
      ],
    } as Order;
    component.orders.set([order]);
    preOrdersServiceMock.editPreOrderByReservationId.and.returnValue(of({}));

    component.removeDishFromOrder('order-1', 'dish-1');

    expect(component.orders()).toEqual([]);
    expect(preOrdersServiceMock.editPreOrderByReservationId).not.toHaveBeenCalled();

    tick(200);

    expect(preOrdersServiceMock.editPreOrderByReservationId).toHaveBeenCalledTimes(1);
    expect(
      preOrdersServiceMock.editPreOrderByReservationId.calls.mostRecent().args[1].orderItems
    ).toEqual([]);
  }));
});
