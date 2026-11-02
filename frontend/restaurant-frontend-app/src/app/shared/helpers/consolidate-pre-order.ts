import { GroupOrderItem, Participant } from '@app/models/group-orders/group-order.model';

export function consolidatePreOrder(participants: Participant[]): GroupOrderItem[] {
  const itemsByDish = new Map<string, GroupOrderItem>();

  for (const participant of participants) {
    if (!participant.isSubmitted) continue;

    for (const item of participant.items) {
      const existing = itemsByDish.get(item.dish.id);
      if (existing) {
        existing.quantity += item.quantity;
      } else {
        itemsByDish.set(item.dish.id, {
          dish: item.dish,
          quantity: item.quantity,
        });
      }
    }
  }

  return [...itemsByDish.values()];
}
