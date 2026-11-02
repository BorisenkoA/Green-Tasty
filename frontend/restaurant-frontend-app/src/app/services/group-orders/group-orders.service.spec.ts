import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { API_BASE_URL } from '@app/shared/config/api-base-url.token';
import { GroupOrdersService } from './group-orders.service';

const BASE_URL = 'https://test.api';

describe('GroupOrdersService', () => {
  let service: GroupOrdersService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: API_BASE_URL, useValue: BASE_URL },
      ],
    });
    service = TestBed.inject(GroupOrdersService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('loads all participant sessions for a group reservation', () => {
    const response = { participants: [], total: 0 };
    service.getSessions$('group-1').subscribe((result) => expect(result).toEqual(response));

    const request = httpMock.expectOne(`${BASE_URL}/guest/groups/group-1/sessions`);
    expect(request.request.method).toBe('GET');
    request.flush(response);
  });

  it('loads the owner session id for a reservation', () => {
    service
      .getGuestSessionId$('reservation-1')
      .subscribe((result) => expect(result.guestSessionId).toBe('owner-session'));

    const request = httpMock.expectOne(`${BASE_URL}/reservations/reservation-1/guest-session-id`);
    expect(request.request.method).toBe('GET');
    request.flush({ guestSessionId: 'owner-session' });
  });

  it('loads group status', () => {
    service.getStatus$('group-1').subscribe((result) => expect(result.status).toBe('Open'));

    const request = httpMock.expectOne(`${BASE_URL}/guest/groups/group-1/status`);
    expect(request.request.method).toBe('GET');
    request.flush({ currentParticipants: 4, maxCapacity: 5, status: 'Open' });
  });

  it('submits the group pre-order with its reservation id', () => {
    service.submit$('group-1', 'reservation-1').subscribe();

    const request = httpMock.expectOne(`${BASE_URL}/group-reservations/group-1/submit`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ reservationId: 'reservation-1' });
    request.flush(null);
  });
});
