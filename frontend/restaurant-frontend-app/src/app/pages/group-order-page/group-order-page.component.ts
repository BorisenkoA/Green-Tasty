import { CurrencyPipe, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { forkJoin, map, switchMap } from 'rxjs';
import { GuestInvite } from '@app/models/reservations/guest-invite.model';
import {
  GroupOrderItem,
  GroupReservationStatus,
  Participant,
} from '@app/models/group-orders/group-order.model';
import { GroupOrdersService } from '@app/services/group-orders/group-orders.service';
import { GuestInviteService } from '@app/services/reservation/guest-invite.service';
import { ToastService } from '@app/services/toast/toast.service';
import { ParticipantCardComponent } from '@app/components/group-orders/participant-card/participant-card.component';
import { ModalComponent } from '@app/shared/custom-components/modal/modal.component';
import { CustomButtonComponent } from '@app/shared/custom-components/custom-button/custom-button.component';
import { consolidatePreOrder } from '@app/shared/helpers/consolidate-pre-order';

@Component({
  selector: 'app-group-order-page',
  standalone: true,
  imports: [
    CurrencyPipe,
    DatePipe,
    ParticipantCardComponent,
    ModalComponent,
    CustomButtonComponent,
  ],
  templateUrl: './group-order-page.component.html',
  styleUrl: './group-order-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GroupOrderPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly inviteService = inject(GuestInviteService);
  private readonly groupOrdersService = inject(GroupOrdersService);
  private readonly toast = inject(ToastService);
  private readonly destroyRef = inject(DestroyRef);

  readonly invite = signal<GuestInvite | null>(null);
  readonly participants = signal<Participant[]>([]);
  readonly guestSessionId = signal<string | null>(null);
  readonly groupStatus = signal<GroupReservationStatus['status'] | null>(null);
  readonly loading = signal(true);
  readonly loadError = signal<string | null>(null);
  readonly submitting = signal(false);
  readonly showSubmitModal = signal(false);
  readonly submitError = signal<string | null>(null);

  readonly consolidatedItems = computed(() => consolidatePreOrder(this.participants()));
  readonly grandTotal = computed(() =>
    this.consolidatedItems().reduce((sum, item) => sum + item.dish.price * item.quantity, 0)
  );
  readonly hasUnsubmittedParticipants = computed(() =>
    this.participants().some((participant) => !participant.isSubmitted)
  );
  readonly unsubmittedCount = computed(
    () => this.participants().filter((participant) => !participant.isSubmitted).length
  );
  readonly isSubmitted = computed(() => this.groupStatus() === 'Submitted');
  readonly isClosed = computed(() => this.groupStatus() === 'Closed');
  readonly submitDisabled = computed(
    () =>
      this.submitting() ||
      this.isSubmitted() ||
      this.isClosed() ||
      this.consolidatedItems().length === 0
  );

  constructor() {
    this.load();
  }

  load(): void {
    const reservationId = this.route.snapshot.paramMap.get('reservationId');
    this.loading.set(true);
    this.loadError.set(null);

    if (!reservationId) {
      this.loading.set(false);
      this.loadError.set('Group reservation not found');
      return;
    }

    this.inviteService
      .getInviteToken$(reservationId)
      .pipe(
        switchMap(({ token }) => this.inviteService.getInvite$(token)),
        switchMap((invite) =>
          forkJoin({
            sessions: this.groupOrdersService.getSessions$(invite.GroupReservationId),
            guestSession: this.groupOrdersService.getGuestSessionId$(reservationId),
            status: this.groupOrdersService.getStatus$(invite.GroupReservationId),
          }).pipe(map((result) => ({ invite, ...result })))
        ),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: ({ invite, sessions, guestSession, status }) => {
          this.invite.set(invite);
          this.participants.set(sessions.participants);
          this.guestSessionId.set(guestSession.guestSessionId);
          this.groupStatus.set(status.status);
          this.loading.set(false);
        },
        error: (error: unknown) => {
          this.loadError.set(
            error instanceof HttpErrorResponse && error.status === 404
              ? 'Group reservation not found'
              : 'Unable to load the group pre-order'
          );
          this.loading.set(false);
        },
      });
  }

  openSubmitDialog(): void {
    if (this.submitDisabled()) return;
    this.submitError.set(null);
    this.showSubmitModal.set(true);
  }

  closeSubmitDialog(): void {
    if (!this.submitting()) this.showSubmitModal.set(false);
  }

  submit(): void {
    const invite = this.invite();
    const reservationId = this.route.snapshot.paramMap.get('reservationId');
    if (!invite || !reservationId || this.submitDisabled()) return;

    this.submitting.set(true);
    this.submitError.set(null);
    this.groupOrdersService
      .submit$(invite.GroupReservationId, reservationId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.groupStatus.set('Submitted');
          this.submitting.set(false);
          this.showSubmitModal.set(false);
          this.toast.success('Pre-order sent to the restaurant');
        },
        error: () => {
          this.submitting.set(false);
          this.submitError.set('Could not send the pre-order. Please try again.');
        },
      });
  }

  itemTotal(item: GroupOrderItem): number {
    return item.dish.price * item.quantity;
  }
}
