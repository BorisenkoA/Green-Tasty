import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TimeSlotsModalComponent } from './time-slots-modal.component';

describe('TimeSlotsModalComponent', () => {
  let component: TimeSlotsModalComponent;
  let fixture: ComponentFixture<TimeSlotsModalComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TimeSlotsModalComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(TimeSlotsModalComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('locationName', 'Test location');
    fixture.componentRef.setInput('table', {
      id: 'table-1',
      tableNumber: 1,
      locationId: 'location-1',
      capacity: 4,
      timeRanges: [{ start: '2026-10-17T10:00:00Z', end: '2026-10-17T11:00:00Z' }],
    });
    fixture.componentRef.setInput('date', '2026-10-17');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
