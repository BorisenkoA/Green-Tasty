import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '@app/shared/config/api-base-url.token';
import {
  GroupOrderSessionsResponse,
  GroupReservationStatus,
  OwnerGuestSessionResponse,
} from '@app/models/group-orders/group-order.model';

@Injectable({ providedIn: 'root' })
export class GroupOrdersService {
  private readonly baseUrl = inject(API_BASE_URL);
  private readonly http = inject(HttpClient);

  getSessions$(groupReservationId: string): Observable<GroupOrderSessionsResponse> {
    return this.http.get<GroupOrderSessionsResponse>(
      `${this.baseUrl}/guest/groups/${encodeURIComponent(groupReservationId)}/sessions`
    );
  }

  getGuestSessionId$(reservationId: string): Observable<OwnerGuestSessionResponse> {
    return this.http.get<OwnerGuestSessionResponse>(
      `${this.baseUrl}/reservations/${encodeURIComponent(reservationId)}/guest-session-id`
    );
  }

  getStatus$(groupReservationId: string): Observable<GroupReservationStatus> {
    return this.http.get<GroupReservationStatus>(
      `${this.baseUrl}/guest/groups/${encodeURIComponent(groupReservationId)}/status`
    );
  }

  submit$(groupReservationId: string, reservationId: string): Observable<void> {
    return this.http.post<void>(
      `${this.baseUrl}/group-reservations/${encodeURIComponent(groupReservationId)}/submit`,
      { reservationId }
    );
  }
}
