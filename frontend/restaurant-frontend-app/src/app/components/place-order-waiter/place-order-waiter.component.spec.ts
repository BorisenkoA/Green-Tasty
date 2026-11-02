import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PlaceOrderWaiterComponent } from './place-order-waiter.component';
import { API_BASE_URL } from '@app/shared/config/api-base-url.token';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { AuthenticationService } from '@app/auth/services/authentication.service';
import { of } from 'rxjs';

describe('PlaceOrderWaiterComponent', () => {
  let component: PlaceOrderWaiterComponent;
  let fixture: ComponentFixture<PlaceOrderWaiterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        { provide: API_BASE_URL, useValue: 'https://test.api' },
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: AuthenticationService,
          useValue: {
            getUser: () => ({ id: 'waiter-1', firstName: 'Test', lastName: 'Waiter' }),
            getUserNameById$: () => of('Test Customer'),
          },
        },
      ],
      imports: [PlaceOrderWaiterComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(PlaceOrderWaiterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
