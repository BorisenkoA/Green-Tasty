import { isDevMode } from '@angular/core';
import { HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { of } from 'rxjs';
import { delay } from 'rxjs/operators';
import {
  DEMO_GROUP_RESERVATION_ID,
  DEMO_GROUP_SESSIONS,
  DEMO_GUEST_INVITE,
  DEMO_GROUP_STATUS,
  DEMO_INVITE_TOKEN,
  DEMO_OWNER_SESSION_ID,
} from './group-order.mock';

let demoStatus = DEMO_GROUP_STATUS.status;

export const groupOrderMockInterceptor: HttpInterceptorFn = (request, next) => {
  if (!isDevMode()) return next(request);

  const path = new URL(request.url, window.location.origin).pathname;
  let body: unknown;

  if (request.method === 'GET' && path.endsWith('/reservations/demo-reservation/invite-token')) {
    body = { token: DEMO_INVITE_TOKEN };
  } else if (request.method === 'GET' && path.endsWith(`/guest/invites/${DEMO_INVITE_TOKEN}`)) {
    body = DEMO_GUEST_INVITE;
  } else if (
    request.method === 'GET' &&
    path.endsWith(`/guest/groups/${DEMO_GROUP_RESERVATION_ID}/sessions`)
  ) {
    body = DEMO_GROUP_SESSIONS;
  } else if (
    request.method === 'GET' &&
    path.endsWith('/reservations/demo-reservation/guest-session-id')
  ) {
    body = { guestSessionId: DEMO_OWNER_SESSION_ID };
  } else if (
    request.method === 'GET' &&
    path.endsWith(`/guest/groups/${DEMO_GROUP_RESERVATION_ID}/status`)
  ) {
    body = { ...DEMO_GROUP_STATUS, status: demoStatus };
  } else if (
    request.method === 'POST' &&
    path.endsWith(`/group-reservations/${DEMO_GROUP_RESERVATION_ID}/submit`)
  ) {
    demoStatus = 'Submitted';
    return of(new HttpResponse<void>({ status: 204 })).pipe(delay(120));
  } else {
    return next(request);
  }

  return of(new HttpResponse({ body })).pipe(delay(120));
};
