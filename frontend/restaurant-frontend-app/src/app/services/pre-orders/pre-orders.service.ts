import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { API_BASE_URL } from '@app/shared/config/api-base-url.token';
import { Order } from '@app/models/orders/order.model';
import { DishListResponse } from '@app/models/dishes/dish-list-response.model';
import {
  catchError,
  concatMap,
  defer,
  Observable,
  finalize,
  map,
  of,
  shareReplay,
  switchMap,
  tap,
} from 'rxjs';
import { CreateOrderRequest } from '@app/models/cart/create-order-request.model';

@Injectable({
  providedIn: 'root',
})
export class PreOrdersService {
  private readonly baseUrl = inject(API_BASE_URL);
  private readonly http = inject(HttpClient);

  private readonly cacheDurationMs = 30_000;
  private cachedOrders: Order[] | null = null;
  private cachedOrdersAt = 0;
  private ordersRequest: Observable<Order[]> | null = null;
  private readonly reservationAddOperations = new Map<string, Observable<unknown>>();

  getPreOrders() {
    if (this.cachedOrders && Date.now() - this.cachedOrdersAt < this.cacheDurationMs) {
      return of(this.copyOrders(this.cachedOrders));
    }

    if (this.ordersRequest) {
      return this.ordersRequest.pipe(map((orders) => this.copyOrders(orders)));
    }

    const request = this.http.get<Order[]>(`${this.baseUrl}/orders`).pipe(
      tap((orders) => {
        this.cachedOrders = this.copyOrders(orders);
        this.cachedOrdersAt = Date.now();
      }),
      finalize(() => {
        this.ordersRequest = null;
      }),
      shareReplay({ bufferSize: 1, refCount: false })
    );
    this.ordersRequest = request;
    return request.pipe(map((orders) => this.copyOrders(orders)));
  }

  getByReservationId(reservationId: string) {
    return this.http.get<Order>(`${this.baseUrl}/orders/${reservationId}`);
  }

  addDishToPreOrderByReservationId(
    reservationId: string,
    dish: DishListResponse,
    quantity: number
  ) {
    return defer(() => {
      const previousOperation = this.reservationAddOperations.get(reservationId) ?? of(null);
      let operation: Observable<unknown>;

      operation = previousOperation.pipe(
        catchError(() => of(null)),
        concatMap(() => this.applyDishAddition(reservationId, dish, quantity)),
        shareReplay({ bufferSize: 1, refCount: false }),
        finalize(() => {
          if (this.reservationAddOperations.get(reservationId) === operation) {
            this.reservationAddOperations.delete(reservationId);
          }
        })
      );
      this.reservationAddOperations.set(reservationId, operation);

      return operation;
    });
  }

  private applyDishAddition(
    reservationId: string,
    dish: DishListResponse,
    quantity: number
  ): Observable<unknown> {
    return this.getPreOrders().pipe(
      map((orders) => {
        const order = orders.find((item) => item.reservationId === reservationId);
        if (!order) {
          return order;
        }

        const existingItem = order.orderItems.find((item) => item.dish.id === dish.id);
        if (existingItem) {
          existingItem.quantity += quantity;
        } else {
          order.orderItems.push({ dish, quantity, state: 0 });
        }
        return order;
      }),
      switchMap((order) => {
        if (!order) {
          const orderCreateRequest: CreateOrderRequest = {
            reservationId,
            orderItems: [{ dish, quantity, state: 0 }],
          };
          return this.createPreOrder(orderCreateRequest);
        }

        return this.editPreOrderByReservationId(reservationId, order);
      })
    );
  }

  createPreOrder(order: CreateOrderRequest) {
    const createOrderRequest = {
      reservationId: order.reservationId,
      orderItems: order.orderItems.map((item) => ({
        dishId: item.dish.id,
        quantity: item.quantity,
      })),
    };

    return this.http
      .post<Order>(`${this.baseUrl}/orders`, createOrderRequest)
      .pipe(tap(() => this.invalidateOrdersCache()));
  }

  editPreOrderByReservationId(reservationId: string, order: Order) {
    const orderItems = order.orderItems.map((item) => ({
      dishId: item.dish.id,
      quantity: item.quantity,
    }));

    if (orderItems.length === 0) {
      return this.cancelPreOrderByReservationId(reservationId);
    }

    return this.http
      .put(`${this.baseUrl}/orders/${reservationId}`, { orderItems })
      .pipe(tap(() => this.invalidateOrdersCache()));
  }

  cancelPreOrderByReservationId(reservationId: string) {
    return this.http
      .delete(`${this.baseUrl}/orders/${reservationId}`)
      .pipe(tap(() => this.invalidateOrdersCache()));
  }

  submitPreOrderByReservationId(reservationId: string) {
    return this.http
      .post(`${this.baseUrl}/orders/${reservationId}/submit`, {})
      .pipe(tap(() => this.invalidateOrdersCache()));
  }

  unsubmitPreOrderByReservationId(reservationId: string) {
    return this.http
      .post(`${this.baseUrl}/orders/${reservationId}/unsubmit`, {})
      .pipe(tap(() => this.invalidateOrdersCache()));
  }

  confirmDishInOrder(reservationId: string, dishId: string) {
    return this.http
      .patch(`${this.baseUrl}/reservations/${reservationId}/order/confirmations/${dishId}`, {})
      .pipe(tap(() => this.invalidateOrdersCache()));
  }

  rejectDishInOrder(reservationId: string, dishId: string) {
    return this.http
      .patch(`${this.baseUrl}/reservations/${reservationId}/order/cancellations/${dishId}`, {})
      .pipe(tap(() => this.invalidateOrdersCache()));
  }

  private invalidateOrdersCache(): void {
    this.cachedOrders = null;
    this.cachedOrdersAt = 0;
  }

  private copyOrders(orders: Order[]): Order[] {
    return orders.map((order) => ({
      ...order,
      orderItems: order.orderItems.map((item) => ({
        ...item,
        dish: { ...item.dish },
      })),
    }));
  }
}
