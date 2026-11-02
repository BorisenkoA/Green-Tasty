import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, UrlTree, provideRouter } from '@angular/router';
import { API_BASE_URL } from '@app/shared/config/api-base-url.token';
import { AuthenticationService } from '../services/authentication.service';

import { AdminGuard } from './admin.guard';

describe('AdminGuard', () => {
  let guard: AdminGuard;
  let router: Router;
  let authService: jasmine.SpyObj<AuthenticationService>;

  beforeEach(() => {
    authService = jasmine.createSpyObj<AuthenticationService>('AuthenticationService', ['getUser']);
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: API_BASE_URL, useValue: 'https://test.api' },
        { provide: AuthenticationService, useValue: authService },
      ],
    });
    guard = TestBed.inject(AdminGuard);
    router = TestBed.inject(Router);
  });

  it('should be created', () => {
    expect(guard).toBeTruthy();
  });

  it('allows administrators to open protected pages', () => {
    authService.getUser.and.returnValue({
      id: 'admin-1',
      firstName: 'Ada',
      lastName: 'Lovelace',
      email: 'ada@example.test',
      role: 'Admin',
    });

    expect(guard.canActivate()).toBeTrue();
  });

  it('redirects signed-in non-administrators to the main page', () => {
    authService.getUser.and.returnValue({
      id: 'customer-1',
      firstName: 'Sam',
      lastName: 'Guest',
      email: 'sam@example.test',
      role: 'Customer',
    });

    const result = guard.canActivate();
    expect(result instanceof UrlTree).toBeTrue();
    expect(router.serializeUrl(result as UrlTree)).toBe('/main');
  });

  it('redirects users without a session to login', () => {
    authService.getUser.and.returnValue(null);

    const result = guard.canActivate();
    expect(result instanceof UrlTree).toBeTrue();
    expect(router.serializeUrl(result as UrlTree)).toBe('/login');
  });
});
