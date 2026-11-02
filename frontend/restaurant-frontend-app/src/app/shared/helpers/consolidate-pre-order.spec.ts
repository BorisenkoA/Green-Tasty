import { DEMO_GROUP_SESSIONS } from '@app/shared/mocks/group-orders/group-order.mock';
import { consolidatePreOrder } from './consolidate-pre-order';

describe('consolidatePreOrder', () => {
  it('includes only submitted carts and produces the expected demo total', () => {
    const items = consolidatePreOrder(DEMO_GROUP_SESSIONS.participants);

    expect(items.reduce((total, item) => total + item.dish.price * item.quantity, 0)).toBe(540);
    expect(items.some((item) => item.dish.id === 'caesar-salad')).toBeFalse();
  });

  it('combines quantities for the same dish across submitted participants', () => {
    const items = consolidatePreOrder(DEMO_GROUP_SESSIONS.participants);
    const avocadoToast = items.find((item) => item.dish.id === 'avocado-toast');

    expect(avocadoToast?.quantity).toBe(8);
  });

  it('returns an empty order when there are no submitted carts', () => {
    const participants = DEMO_GROUP_SESSIONS.participants.map((participant) => ({
      ...participant,
      isSubmitted: false,
    }));

    expect(consolidatePreOrder(participants)).toEqual([]);
  });
});
