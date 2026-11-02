import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { provideRouter } from '@angular/router';

import { HeaderComponent } from './header.component';
import { API_BASE_URL } from '@app/shared/config/api-base-url.token';
import { AuthenticationService } from '@app/auth/services/authentication.service';
import { NotificationsService } from '@app/services/notifications/notifications.service';
import { PreOrdersService } from '@app/services/pre-orders/pre-orders.service';
import { UserModel } from '@app/auth/models/user.model';

describe('HeaderComponent', () => {
  let component: HeaderComponent;
  let fixture: ComponentFixture<HeaderComponent>;

  let authMock: jasmine.SpyObj<AuthenticationService>;
  let notificationsMock: jasmine.SpyObj<NotificationsService>;
  let preOrdersMock: jasmine.SpyObj<PreOrdersService>;

  beforeEach(async () => {
    authMock = jasmine.createSpyObj<AuthenticationService>('AuthenticationService', ['signOut'], {
      user$: of(null),
      isAuthorised$: of(false),
    });

    notificationsMock = jasmine.createSpyObj<NotificationsService>('NotificationsService', [
      'loadNotifications',
      'markAsRead',
    ]);

    notificationsMock.loadNotifications.and.returnValue(of([]));
    notificationsMock.markAsRead.and.returnValue(of(void 0));

    preOrdersMock = jasmine.createSpyObj<PreOrdersService>('PreOrdersService', ['getPreOrders']);
    preOrdersMock.getPreOrders.and.returnValue(of([]));

    await TestBed.configureTestingModule({
      providers: [
        { provide: API_BASE_URL, useValue: 'https://test.api' },
        { provide: AuthenticationService, useValue: authMock },
        { provide: NotificationsService, useValue: notificationsMock },
        { provide: PreOrdersService, useValue: preOrdersMock },
        provideRouter([]),
      ],
      imports: [HeaderComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(HeaderComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should preload customer pre-orders before the cart is opened', () => {
    component.user.set({ role: 'Customer' } as UserModel);
    fixture.detectChanges();

    expect(preOrdersMock.getPreOrders).toHaveBeenCalled();
  });

  it('should show a dedicated cart button for customers outside the mobile menu', () => {
    component.user.set({ role: 'Customer' } as UserModel);
    fixture.detectChanges();

    const cartButton = fixture.nativeElement.querySelector(
      '.mobile-cart-button'
    ) as HTMLButtonElement | null;

    expect(cartButton).not.toBeNull();
    expect(cartButton?.getAttribute('aria-label')).toBe('Open cart');
  });

  it('should expose the mobile menu state accessibly', () => {
    const menuButton = fixture.nativeElement.querySelector(
      '.mobile-menu-icon'
    ) as HTMLButtonElement;

    expect(menuButton.getAttribute('aria-expanded')).toBe('false');
    expect(menuButton.getAttribute('aria-label')).toBe('Open menu');

    menuButton.click();
    fixture.detectChanges();

    expect(menuButton.getAttribute('aria-expanded')).toBe('true');
    expect(menuButton.getAttribute('aria-label')).toBe('Close menu');
    expect(menuButton.classList).toContain('is-open');
  });
});
