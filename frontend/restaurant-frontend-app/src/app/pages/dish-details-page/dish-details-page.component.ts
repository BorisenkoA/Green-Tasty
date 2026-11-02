import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DishListResponse } from '@app/models/dishes/dish-list-response.model';
import { DishesService } from '@app/services/dishes/dishes.service';
import { ToastService } from '@app/services/toast/toast.service';

const FAVORITES_STORAGE_KEY = 'favorite-dish-ids';

@Component({
  selector: 'app-dish-details-page',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './dish-details-page.component.html',
  styleUrl: './dish-details-page.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class DishDetailsPageComponent implements OnInit {
  readonly dish = signal<DishListResponse | null>(null);
  readonly loading = signal(true);
  readonly errorMessage = signal('');
  readonly isFavorite = signal(false);

  private readonly route = inject(ActivatedRoute);
  private readonly dishesService = inject(DishesService);
  private readonly toast = inject(ToastService);

  ngOnInit(): void {
    const dishId = this.route.snapshot.paramMap.get('id');
    if (!dishId) {
      this.loading.set(false);
      this.errorMessage.set('This dish could not be found.');
      return;
    }

    this.isFavorite.set(this.readFavoriteIds().includes(dishId));
    this.dishesService.getDishById(dishId).subscribe({
      next: (dish) => {
        this.dish.set({
          ...dish,
          imageUrl: dish.imageUrl || 'assets/img/dish.png',
        });
        this.loading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.loading.set(false);
        this.errorMessage.set(
          error.status === 404
            ? 'This dish is no longer on the menu.'
            : 'We could not load this dish. Please try again later.'
        );
        console.error('Failed to load dish details:', error);
      },
    });
  }

  toggleFavorite(): void {
    const currentDish = this.dish();
    if (!currentDish) return;

    const favoriteIds = this.readFavoriteIds();
    const nextIds = this.isFavorite()
      ? favoriteIds.filter((id) => id !== currentDish.id)
      : [...new Set([...favoriteIds, currentDish.id])];

    try {
      localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(nextIds));
      this.isFavorite.set(!this.isFavorite());
      this.toast.success(
        this.isFavorite() ? 'Saved to your favorites.' : 'Removed from your favorites.',
        this.isFavorite() ? 'Saved' : 'Removed'
      );
    } catch (error) {
      console.error('Failed to save favorite dishes:', error);
      this.toast.error('Your favorites could not be saved in this browser.', 'Unable to save');
    }
  }

  async shareDish(): Promise<void> {
    const currentDish = this.dish();
    if (!currentDish) return;

    const shareData = {
      title: currentDish.name,
      text: `Take a look at ${currentDish.name} on Green & Tasty.`,
      url: window.location.href,
    };

    try {
      if (navigator.share) {
        await navigator.share(shareData);
      } else {
        await navigator.clipboard.writeText(shareData.url);
        this.toast.success('Dish link copied to clipboard.', 'Ready to share');
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      console.error('Failed to share dish:', error);
      this.toast.error(
        'The dish link could not be shared. Please copy the page URL.',
        'Share failed'
      );
    }
  }

  formatNutritionValue(value: string, unit: 'g' | 'kcal'): string {
    const normalizedValue = value
      .trim()
      .replace(new RegExp(`(?:\\s*${unit})+$`, 'i'), '')
      .trim();

    return `${normalizedValue} ${unit}`;
  }

  private readFavoriteIds(): string[] {
    try {
      const saved = localStorage.getItem(FAVORITES_STORAGE_KEY);
      if (!saved) return [];

      const parsed: unknown = JSON.parse(saved);
      if (Array.isArray(parsed) && parsed.every((id) => typeof id === 'string')) {
        return parsed;
      }

      console.error('Saved favorite dish data has an unexpected format.');
    } catch (error) {
      console.error('Failed to read favorite dishes:', error);
    }

    return [];
  }
}
