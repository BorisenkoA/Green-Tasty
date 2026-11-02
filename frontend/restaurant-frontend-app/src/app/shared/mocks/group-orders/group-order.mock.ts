import {
  GroupOrderSessionsResponse,
  GroupReservationStatus,
  Participant,
} from '@app/models/group-orders/group-order.model';

export const DEMO_GROUP_RESERVATION_ID = 'demo-group-reservation';
export const DEMO_INVITE_TOKEN = 'demo-group-invite';
export const DEMO_OWNER_SESSION_ID = 'demo-owner-session';

const participants: Participant[] = [
  {
    id: DEMO_OWNER_SESSION_ID,
    type: 'Owner',
    name: 'Yevhenii',
    items: [
      {
        dish: {
          id: 'strawberry-salad',
          name: 'Fresh Strawberry Mint Salad',
          price: 34,
          imageUrl: 'assets/img/dishes/fresh-strawberry-mint-salad.jpg',
        },
        quantity: 2,
      },
      {
        dish: { id: 'green-bowl', name: 'Green Bowl', price: 14.5 },
        quantity: 4,
      },
      {
        dish: { id: 'avocado-toast', name: 'Avocado Toast', price: 10 },
        quantity: 7,
      },
      {
        dish: { id: 'tea', name: 'Black Tea', price: 4 },
        quantity: 1,
      },
    ],
    total: 200,
    isSubmitted: true,
  },
  {
    id: 'demo-guest-kateryna',
    type: 'Guest',
    name: 'Kateryna',
    items: [
      {
        dish: { id: 'grilled-salmon', name: 'Grilled Salmon', price: 40 },
        quantity: 3,
      },
      {
        dish: { id: 'lemonade', name: 'Fresh Lemonade', price: 10 },
        quantity: 4,
      },
    ],
    total: 160,
    isSubmitted: true,
  },
  {
    id: 'demo-guest-maria',
    type: 'Guest',
    name: 'Maria',
    items: [
      {
        dish: {
          id: 'quinoa-salad',
          name: 'Quinoa Salad',
          price: 14,
          imageUrl: 'assets/img/dishes/roasted-sweet-potato-and-lentil-salad.jpg',
        },
        quantity: 5,
      },
      {
        dish: { id: 'mushroom-risotto', name: 'Mushroom Risotto', price: 17 },
        quantity: 4,
      },
      {
        dish: { id: 'sparkling-water', name: 'Sparkling Water', price: 7 },
        quantity: 2,
      },
      {
        dish: { id: 'avocado-toast', name: 'Avocado Toast', price: 10 },
        quantity: 1,
      },
      {
        dish: { id: 'tea', name: 'Black Tea', price: 4 },
        quantity: 2,
      },
      {
        dish: { id: 'lemonade', name: 'Fresh Lemonade', price: 10 },
        quantity: 1,
      },
    ],
    total: 180,
    isSubmitted: true,
  },
  {
    id: 'demo-guest-olena',
    type: 'Guest',
    name: 'Olena',
    items: [
      {
        dish: { id: 'caesar-salad', name: 'Caesar Salad', price: 22 },
        quantity: 5,
      },
      {
        dish: { id: 'sparkling-water', name: 'Sparkling Water', price: 7 },
        quantity: 10,
      },
      {
        dish: { id: 'lemonade', name: 'Fresh Lemonade', price: 10 },
        quantity: 4,
      },
    ],
    total: 220,
    isSubmitted: false,
  },
];

export const DEMO_GROUP_SESSIONS: GroupOrderSessionsResponse = {
  participants,
  total: 760,
};

export const DEMO_GROUP_STATUS: GroupReservationStatus = {
  currentParticipants: participants.length,
  maxCapacity: 5,
  status: 'Open',
};

export const DEMO_GUEST_INVITE = {
  GroupReservationId: DEMO_GROUP_RESERVATION_ID,
  LocationId: 'demo-location',
  RestaurantName: 'Green & Tasty',
  LocationAddress: '48 Rustaveli Avenue',
  StartTime: '2026-10-17T12:00:00',
  EndTime: '2026-10-17T14:00:00',
  MaxGuestCount: 5,
  TableNumber: 8,
  InviterName: 'Yevhenii',
};
