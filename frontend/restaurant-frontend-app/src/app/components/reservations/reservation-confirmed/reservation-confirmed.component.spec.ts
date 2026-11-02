import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ReservationConfirmedComponent } from './reservation-confirmed.component';

describe('ReservationConfirmedComponent', () => {
  let component: ReservationConfirmedComponent;
  let fixture: ComponentFixture<ReservationConfirmedComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReservationConfirmedComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ReservationConfirmedComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('reservation', {
      id: 'reservation-1',
      tableId: 'table-1',
      customerId: 'customer-1',
      startTime: new Date('2026-10-17T10:00:00Z'),
      endTime: new Date('2026-10-17T11:00:00Z'),
      guestCount: 2,
      status: 0,
      locationAddress: 'Test address',
      tableCapacity: 4,
      waiterId: 'waiter-1',
    });
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
