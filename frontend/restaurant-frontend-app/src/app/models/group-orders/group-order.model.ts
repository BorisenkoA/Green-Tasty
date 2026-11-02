export interface GroupOrderDish {
  id: string;
  name: string;
  price: number;
  imageUrl?: string | null;
}

export interface GroupOrderItem {
  dish: GroupOrderDish;
  quantity: number;
}

export interface Participant {
  id: string | null;
  type: 'Owner' | 'Guest';
  name: string;
  items: GroupOrderItem[];
  total: number;
  isSubmitted: boolean;
}

export interface GroupOrderSessionsResponse {
  participants: Participant[];
  total: number;
}

export interface GroupReservationStatus {
  currentParticipants: number;
  maxCapacity: number;
  status: 'Open' | 'Submitted' | 'Closed';
}

export interface OwnerGuestSessionResponse {
  guestSessionId: string;
}
