import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of, throwError } from 'rxjs';
import { GuestInvite } from '@app/models/reservations/guest-invite.model';
import { GroupOrdersService } from '@app/services/group-orders/group-orders.service';
import { GuestInviteService } from '@app/services/reservation/guest-invite.service';
import { ToastService } from '@app/services/toast/toast.service';
import {
  DEMO_GROUP_SESSIONS,
  DEMO_GROUP_STATUS,
  DEMO_GUEST_INVITE,
  DEMO_OWNER_SESSION_ID,
} from '@app/shared/mocks/group-orders/group-order.mock';
import { GroupOrderPageComponent } from './group-order-page.component';

const DEMO_INVITE: GuestInvite = DEMO_GUEST_INVITE;

describe('GroupOrderPageComponent', () => {
  let fixture: ComponentFixture<GroupOrderPageComponent>;
  let groupOrders: jasmine.SpyObj<GroupOrdersService>;
  let guestInvite: jasmine.SpyObj<GuestInviteService>;
  let toast: jasmine.SpyObj<ToastService>;

  beforeEach(() => {
    groupOrders = jasmine.createSpyObj<GroupOrdersService>('GroupOrdersService', [
      'getSessions$',
      'getGuestSessionId$',
      'getStatus$',
      'submit$',
    ]);
    guestInvite = jasmine.createSpyObj<GuestInviteService>('GuestInviteService', [
      'getInviteToken$',
      'getInvite$',
    ]);
    toast = jasmine.createSpyObj<ToastService>('ToastService', ['success']);
    guestInvite.getInviteToken$.and.returnValue(of({ token: 'demo-token' }));
    guestInvite.getInvite$.and.returnValue(of(DEMO_INVITE));
    groupOrders.getSessions$.and.returnValue(of(DEMO_GROUP_SESSIONS));
    groupOrders.getGuestSessionId$.and.returnValue(of({ guestSessionId: DEMO_OWNER_SESSION_ID }));
    groupOrders.getStatus$.and.returnValue(of(DEMO_GROUP_STATUS));
    groupOrders.submit$.and.returnValue(of(undefined));

    TestBed.configureTestingModule({
      imports: [GroupOrderPageComponent],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: convertToParamMap({ reservationId: 'demo-reservation' }) },
          },
        },
        { provide: GroupOrdersService, useValue: groupOrders },
        { provide: GuestInviteService, useValue: guestInvite },
        { provide: ToastService, useValue: toast },
      ],
    });
  });

  function createComponent(): void {
    fixture = TestBed.createComponent(GroupOrderPageComponent);
    fixture.detectChanges();
  }

  it('loads reservation sessions, shows the owner card, and totals submitted carts only', () => {
    createComponent();

    const page = fixture.nativeElement as HTMLElement;
    expect(page.textContent).toContain('My Pre-Order');
    expect(page.textContent).toContain('Guest: Kateryna');
    expect(page.textContent).toContain('$540.00');
    expect(page.querySelector('.consolidated')?.textContent).not.toContain('Caesar Salad');
    expect(page.textContent).toContain("participants haven't submitted their cart yet");
  });

  it('shows a retry action when loading fails', () => {
    guestInvite.getInviteToken$.and.returnValue(throwError(() => new Error('network')));
    createComponent();

    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Try again');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain(
      'Unable to load the group pre-order'
    );
  });

  it('submits once after confirmation and switches to the read-only status', () => {
    createComponent();

    const buttons = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button'));
    buttons.find((button) => button.textContent?.includes('Submit Pre-Order'))?.click();
    fixture.detectChanges();

    const confirmButton = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll('button')
    ).find((button) => button.textContent?.trim() === 'Submit');
    confirmButton?.click();
    fixture.detectChanges();

    expect(groupOrders.submit$).toHaveBeenCalledOnceWith(
      DEMO_INVITE.GroupReservationId,
      'demo-reservation'
    );
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Sent to Restaurant');
    expect(toast.success).toHaveBeenCalledWith('Pre-order sent to the restaurant');
  });
});
