import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  OnInit,
  computed,
  inject,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { forkJoin } from 'rxjs';

import { Order } from '@app/models/orders/order.model';
import { Reservation, ReservationStatus } from '@app/models/reservations/reservation.model';
import { PreOrdersService } from '@app/services/pre-orders/pre-orders.service';
import { ReservationService } from '@app/services/reservation/reservation.service';

import { CancelOrderModalComponent } from './components/cancel-order-modal/cancel-order-modal.component';
import { NotSubmittedOrderComponent } from './components/not-submitted-order/not-submitted-order.component';
import { SubmitOrderModalComponent } from './components/submit-order-modal/submit-order-modal.component';
import { SubmittedOrderComponent } from './components/submitted-order/submitted-order.component';

@Component({
  selector: 'app-cart',
  standalone: true,
  imports: [
    SubmittedOrderComponent,
    NotSubmittedOrderComponent,
    CancelOrderModalComponent,
    SubmitOrderModalComponent,
  ],
  templateUrl: './cart.component.html',
  styleUrl: './cart.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CartComponent implements OnInit {
  private readonly preOrdersService = inject(PreOrdersService);
  private readonly reservationService = inject(ReservationService);

  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly closeCartEvent = output<void>();

  readonly orders = signal<Order[]>([]);
  readonly ordersLoadError = signal(false);

  readonly cancelOrderId = signal<string | null>(null);
  readonly submitOrderId = signal<string | null>(null);

  private readonly quantitySaveTimers = new Map<string, ReturnType<typeof setTimeout>>();
  private readonly quantitySaveVersions = new Map<string, number>();
  private readonly savingQuantityOrders = new Set<string>();
  private readonly confirmedOrders = new Map<string, Order>();
  private readonly pendingOrders = new Map<string, Order>();

  readonly submittedOrders = computed(() =>
    this.orders().filter((order) => order.status === 1 || order.status === 3)
  );

  readonly unsubmittedOrders = computed(() => this.orders().filter((order) => order.status === 0));

  readonly submittedOrder = computed(() => {
    const orderId = this.submitOrderId();

    if (!orderId) {
      return undefined;
    }

    return this.orders().find((order) => order.orderId === orderId);
  });

  ngOnInit(): void {
    this.loadOrders();
  }

  constructor() {
    this.destroyRef.onDestroy(() => {
      this.quantitySaveTimers.forEach((timer) => clearTimeout(timer));
    });
  }

  closeCart(): void {
    this.closeCartEvent.emit();
  }

  openCancelModal(orderId: string): void {
    this.cancelOrderId.set(orderId);
    this.submitOrderId.set(null);
  }

  closeCancelModal(): void {
    this.cancelOrderId.set(null);
  }

  closeSubmitModal(): void {
    this.submitOrderId.set(null);
  }

  editOrderModal(): void {
    const orderId = this.submitOrderId();

    if (!orderId) {
      console.error('No order selected for editing');
      return;
    }

    this.editOrder(orderId);
    this.closeSubmitModal();
  }

  goToReservations(): void {
    this.closeCart();
    void this.router.navigate(['/reservations']);
  }

  cancelOrder(orderId: string): void {
    const order = this.findOrder(orderId);

    if (!order) {
      return;
    }

    this.preOrdersService
      .cancelPreOrderByReservationId(order.reservationId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.closeCancelModal();
          this.loadOrders();
        },
        error: (error) => {
          console.error(`Error cancelling order ${orderId}:`, error);
        },
      });
  }

  editOrder(orderId: string): void {
    const order = this.findOrder(orderId);

    if (!order) {
      return;
    }

    this.preOrdersService
      .unsubmitPreOrderByReservationId(order.reservationId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.loadOrders();
        },
        error: (error) => {
          console.error(`Error un-submitting order ${orderId}:`, error);
        },
      });
  }

  submitOrder(orderId: string): void {
    const order = this.findOrder(orderId);

    if (!order) {
      return;
    }

    this.preOrdersService
      .submitPreOrderByReservationId(order.reservationId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.submitOrderId.set(orderId);
          this.loadOrders();
        },
        error: (error) => {
          console.error(`Error submitting order ${orderId}:`, error);
        },
      });
  }

  addDishToOrder(orderId: string): void {
    const order = this.findOrder(orderId);
    if (!order) {
      return;
    }

    this.closeCart();
    void this.router.navigate(['/menu'], {
      queryParams: {
        preOrder: true,
        reservationId: order.reservationId,
        reservationLabel: order.reservationAddress,
      },
    });
  }

  updateDishQuantity(orderId: string, itemId: string, quantity: number): void {
    if (quantity < 1) {
      return;
    }

    const originalOrder = this.findOrder(orderId);

    if (!originalOrder) {
      return;
    }

    const updatedOrder: Order = {
      ...originalOrder,
      orderItems: originalOrder.orderItems.map((item) =>
        item.dish.id === itemId
          ? {
              ...item,
              quantity,
            }
          : item
      ),
    };

    this.orders.update((orders) =>
      orders.map((order) => (order.orderId === orderId ? updatedOrder : order))
    );
    this.scheduleOrderSave(orderId, updatedOrder);
  }

  removeDishFromOrder(orderId: string, itemId: string): void {
    const originalOrder = this.findOrder(orderId);

    if (!originalOrder) {
      return;
    }

    const updatedOrder: Order = {
      ...originalOrder,
      orderItems: originalOrder.orderItems.filter((item) => item.dish.id !== itemId),
    };

    this.pendingOrders.set(orderId, this.copyOrder(updatedOrder));
    if (updatedOrder.orderItems.length === 0) {
      this.orders.update((orders) => orders.filter((order) => order.orderId !== orderId));
    } else {
      this.orders.update((orders) =>
        orders.map((order) => (order.orderId === orderId ? updatedOrder : order))
      );
    }
    this.scheduleOrderSave(orderId, updatedOrder);
  }

  private findOrder(orderId: string): Order | undefined {
    const order = this.orders().find((item) => item.orderId === orderId);

    if (!order) {
      console.error(`Order with ID ${orderId} not found`);
    }

    return order;
  }

  private loadOrders(): void {
    this.ordersLoadError.set(false);
    forkJoin({
      orders: this.preOrdersService.getPreOrders(),
      reservations: this.reservationService.getReservationsForUser$(),
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: ({ orders, reservations }) => {
          const eligibleReservationIds = new Set(
            reservations
              .filter(
                (reservation: Reservation) => reservation.status !== ReservationStatus.Cancelled
              )
              .map((reservation) => reservation.id)
          );
          const reservationOrders = orders.filter((order) =>
            eligibleReservationIds.has(order.reservationId)
          );

          this.orders.set(reservationOrders);
          this.confirmedOrders.clear();
          reservationOrders.forEach((order) =>
            this.confirmedOrders.set(order.orderId, this.copyOrder(order))
          );
        },
        error: (error) => {
          console.error('Error loading cart orders or reservations:', error);
          this.ordersLoadError.set(true);
        },
      });
  }

  private persistQuantityUpdate(orderId: string, version: number): void {
    if (this.savingQuantityOrders.has(orderId)) {
      return;
    }

    const order =
      this.pendingOrders.get(orderId) ?? this.orders().find((item) => item.orderId === orderId);
    if (!order) {
      return;
    }

    const orderToSave = this.copyOrder(order);
    this.savingQuantityOrders.add(orderId);
    this.preOrdersService
      .editPreOrderByReservationId(orderToSave.reservationId, orderToSave)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.confirmedOrders.set(orderId, orderToSave);
          this.finishQuantitySave(orderId, version);
        },
        error: (error) => {
          console.error(`Error saving order ${orderId}:`, error);
          this.finishQuantitySave(orderId, version, true);
        },
      });
  }

  private finishQuantitySave(orderId: string, savedVersion: number, failed = false): void {
    this.savingQuantityOrders.delete(orderId);

    const currentVersion = this.quantitySaveVersions.get(orderId);
    if (currentVersion !== savedVersion) {
      const timer = this.quantitySaveTimers.get(orderId);
      if (timer) {
        clearTimeout(timer);
        this.quantitySaveTimers.delete(orderId);
      }
      this.persistQuantityUpdate(orderId, currentVersion!);
      return;
    }

    this.pendingOrders.delete(orderId);
    if (failed) {
      const confirmedOrder = this.confirmedOrders.get(orderId);
      if (confirmedOrder) {
        this.orders.update((orders) =>
          orders.some((order) => order.orderId === orderId)
            ? orders.map((order) =>
                order.orderId === orderId ? this.copyOrder(confirmedOrder) : order
              )
            : [...orders, this.copyOrder(confirmedOrder)]
        );
      }
    }
  }

  private scheduleOrderSave(orderId: string, order: Order): void {
    this.pendingOrders.set(orderId, this.copyOrder(order));
    const version = (this.quantitySaveVersions.get(orderId) ?? 0) + 1;
    this.quantitySaveVersions.set(orderId, version);

    const previousTimer = this.quantitySaveTimers.get(orderId);
    if (previousTimer) {
      clearTimeout(previousTimer);
    }

    this.quantitySaveTimers.set(
      orderId,
      setTimeout(() => {
        this.quantitySaveTimers.delete(orderId);
        this.persistQuantityUpdate(orderId, version);
      }, 200)
    );
  }

  private copyOrder(order: Order): Order {
    return {
      ...order,
      orderItems: order.orderItems.map((item) => ({ ...item })),
    };
  }
}
