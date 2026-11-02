import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Participant } from '@app/models/group-orders/participant.model';
import { ParticipantCardComponent } from './participant-card.component';

const PARTICIPANT: Participant = {
  id: 'guest-1',
  type: 'Guest',
  name: 'Kateryna',
  items: [
    {
      dish: {
        id: 'salad',
        name: 'Fresh Salad',
        price: 12.5,
        imageUrl: 'assets/img/dish.png',
      },
      quantity: 2,
    },
  ],
  total: 25,
  isSubmitted: true,
};

describe('ParticipantCardComponent', () => {
  let fixture: ComponentFixture<ParticipantCardComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [ParticipantCardComponent] });
    fixture = TestBed.createComponent(ParticipantCardComponent);
    fixture.componentRef.setInput('participant', PARTICIPANT);
  });

  it('shows the participant role, dish quantity, and subtotal', () => {
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Guest: Kateryna');
    expect(text).toContain('× 2');
    expect(text).toContain('$25.00');
    expect(text).toContain('Submitted');
  });

  it('uses the owner session id for the My Pre-Order title', () => {
    fixture.componentRef.setInput('participant', { ...PARTICIPANT, type: 'Owner' });
    fixture.componentRef.setInput('guestSessionId', 'guest-1');
    fixture.detectChanges();

    expect((fixture.nativeElement as HTMLElement).textContent).toContain('My Pre-Order');
  });

  it('reserves lazy image space using explicit dimensions', () => {
    fixture.detectChanges();

    const image = (fixture.nativeElement as HTMLElement).querySelector('img');
    expect(image?.getAttribute('width')).toBe('40');
    expect(image?.getAttribute('height')).toBe('40');
    expect(image?.getAttribute('loading')).toBe('lazy');
  });
});
