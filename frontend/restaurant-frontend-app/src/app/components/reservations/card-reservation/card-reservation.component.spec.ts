import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CardReservationComponent } from './card-reservation.component';
import { API_BASE_URL } from '@app/shared/config/api-base-url.token';

describe('CardReservationComponent', () => {
  let component: CardReservationComponent;
  let fixture: ComponentFixture<CardReservationComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [{ provide: API_BASE_URL, useValue: 'https://test.api' }],
      imports: [CardReservationComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(CardReservationComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('r', {
      id: 'reservation-1',
      tableId: 'table-1',
      startTime: new Date('2026-10-17T10:00:00Z'),
      endTime: new Date('2026-10-17T11:00:00Z'),
      guestCount: 2,
      status: 0,
      restaurantName: 'Test restaurant',
      locationAddress: 'Test address',
      waiterId: 'waiter-1',
    });
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
