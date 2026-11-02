import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { Participant } from '@app/models/group-orders/group-order.model';

@Component({
  selector: 'app-participant-card',
  standalone: true,
  imports: [CurrencyPipe],
  templateUrl: './participant-card.component.html',
  styleUrl: './participant-card.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ParticipantCardComponent {
  readonly participant = input.required<Participant>();
  readonly guestSessionId = input<string | null>(null);

  readonly title = computed(() => {
    const person = this.participant();
    return person.id && person.id === this.guestSessionId()
      ? 'My Pre-Order'
      : person.type === 'Owner'
        ? `Owner: ${person.name}`
        : `Guest: ${person.name}`;
  });
}
