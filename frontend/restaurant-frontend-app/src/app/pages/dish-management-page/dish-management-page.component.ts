import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { LocationResponse } from '@app/models/locations/location-response.model';
import { DishListResponse } from '@app/models/dishes/dish-list-response.model';
import { CreateDishRequest } from '@app/models/dishes/create-dish-request.model';
import { DishState } from '@app/models/enums/dish-state.model';
import { DishType } from '@app/models/enums/dish-type.model';
import { DishesService } from '@app/services/dishes/dishes.service';
import { LocationsService } from '@app/services/locations/locations.service';
import { ToastService } from '@app/services/toast/toast.service';

interface DishDraft {
  name: string;
  description: string;
  dishType: DishType;
  price: number;
  weight: string;
  calories: string;
  proteins: string;
  fats: string;
  carbohydrates: string;
  vitamins: string;
  state: DishState;
  locationIds: string[];
  imageBase64?: string;
}

const emptyDraft = (): DishDraft => ({
  name: '',
  description: '',
  dishType: DishType.MainCourse,
  price: 0,
  weight: '',
  calories: '0',
  proteins: '0',
  fats: '0',
  carbohydrates: '0',
  vitamins: '',
  state: DishState.Available,
  locationIds: [],
});

@Component({
  selector: 'app-dish-management-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './dish-management-page.component.html',
  styleUrl: './dish-management-page.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class DishManagementPageComponent implements OnInit {
  readonly dishes = signal<DishListResponse[]>([]);
  readonly locations = signal<LocationResponse[]>([]);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly searchText = signal('');
  readonly errorMessage = signal('');
  readonly dishTypes = Object.values(DishType);
  readonly dishStates = Object.values(DishState);

  draft = emptyDraft();
  editingDishId: string | null = null;
  imageFileName = '';

  private readonly dishesService = inject(DishesService);
  private readonly locationsService = inject(LocationsService);
  private readonly toast = inject(ToastService);

  get visibleDishes(): DishListResponse[] {
    const query = this.searchText().trim().toLocaleLowerCase();
    return this.dishes().filter((dish) =>
      `${dish.name} ${dish.dishType} ${dish.description}`.toLocaleLowerCase().includes(query)
    );
  }

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.loading.set(true);
    this.errorMessage.set('');
    forkJoin({
      dishes: this.dishesService.getDishes(),
      locations: this.locationsService.getLocations(),
    }).subscribe({
      next: ({ dishes, locations }) => {
        this.dishes.set(dishes);
        this.locations.set(locations);
        this.loading.set(false);
      },
      error: (error: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(this.describeError(error, 'Could not load menu management data.'));
        console.error('Failed to load menu management data:', error);
      },
    });
  }

  startNewDish(): void {
    this.editingDishId = null;
    this.draft = emptyDraft();
    this.imageFileName = '';
  }

  editDish(dish: DishListResponse): void {
    this.saving.set(true);
    forkJoin(
      this.locations().map((location) => this.dishesService.getDishesByLocationId(location.id))
    ).subscribe({
      next: (dishesByLocation) => {
        const locationIds = this.locations()
          .filter((_, index) => dishesByLocation[index].some((item) => item.id === dish.id))
          .map((location) => location.id);

        this.editingDishId = dish.id;
        this.draft = {
          name: dish.name,
          description: dish.description,
          dishType: this.toDishType(dish.dishType),
          price: dish.price,
          weight: dish.weight,
          calories: dish.calories,
          proteins: dish.proteins,
          fats: dish.fats,
          carbohydrates: dish.carbohydrates,
          vitamins: dish.vitamins,
          state: this.toDishState(dish.state),
          locationIds,
        };
        this.imageFileName = '';
        this.saving.set(false);
        document.querySelector('#dishEditor')?.scrollIntoView({ behavior: 'smooth' });
      },
      error: (error: unknown) => {
        this.saving.set(false);
        this.toast.error(
          this.describeError(error, 'Could not load the dish locations.'),
          'Edit failed'
        );
        console.error('Failed to load dish locations:', error);
      },
    });
  }

  cancelEdit(): void {
    this.startNewDish();
  }

  onSearchInput(event: Event): void {
    this.searchText.set((event.target as HTMLInputElement).value);
  }

  toggleLocation(locationId: string, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    const locationIds = checked
      ? [...new Set([...this.draft.locationIds, locationId])]
      : this.draft.locationIds.filter((id) => id !== locationId);
    this.draft = { ...this.draft, locationIds };
  }

  async onImageSelected(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      input.value = '';
      this.toast.error('Choose an image file.', 'Unsupported file');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      input.value = '';
      this.toast.error('Choose an image smaller than 5 MB.', 'Image is too large');
      return;
    }

    try {
      this.draft = { ...this.draft, imageBase64: await this.readImage(file) };
      this.imageFileName = file.name;
    } catch (error) {
      console.error('Failed to read selected dish image:', error);
      this.toast.error('The selected image could not be read.', 'Image upload failed');
    }
  }

  saveDish(): void {
    if (this.saving()) return;
    if (this.draft.locationIds.length === 0) {
      this.toast.error(
        'Choose at least one restaurant location for this dish.',
        'Location required'
      );
      return;
    }

    const request: CreateDishRequest = {
      name: this.draft.name.trim(),
      description: this.draft.description.trim(),
      dishType: this.draft.dishType,
      price: Number(this.draft.price),
      weight: this.draft.weight.trim(),
      calories: this.draft.calories.trim(),
      proteins: this.draft.proteins.trim(),
      fats: this.draft.fats.trim(),
      carbohydrates: this.draft.carbohydrates.trim(),
      vitamins: this.draft.vitamins.trim(),
      state: this.draft.state,
      locationIds: [...this.draft.locationIds],
      ...(this.draft.imageBase64 ? { imageBase64: this.draft.imageBase64 } : {}),
    };

    if (!Number.isFinite(request.price) || request.price < 0) {
      this.toast.error('Enter a valid non-negative price.', 'Check the price');
      return;
    }

    this.saving.set(true);
    const request$ = this.editingDishId
      ? this.dishesService.updateDish(this.editingDishId, request)
      : this.dishesService.createDish(request);

    request$.subscribe({
      next: () => {
        this.saving.set(false);
        this.toast.success(
          this.editingDishId
            ? 'Dish details have been updated.'
            : 'The dish has been added to the menu.',
          'Menu updated'
        );
        this.startNewDish();
        this.loadData();
      },
      error: (error: unknown) => {
        this.saving.set(false);
        this.toast.error(this.describeError(error, 'The dish could not be saved.'), 'Save failed');
        console.error('Failed to save dish:', error);
      },
    });
  }

  deleteDish(dish: DishListResponse): void {
    const confirmed = window.confirm(
      `Delete "${dish.name}" and remove it from all restaurant menus? This cannot be undone.`
    );
    if (!confirmed) return;

    this.dishesService.deleteDish(dish.id, true).subscribe({
      next: () => {
        this.dishes.update((items) => items.filter((item) => item.id !== dish.id));
        if (this.editingDishId === dish.id) this.startNewDish();
        this.toast.success(`${dish.name} was removed from all menus.`, 'Dish deleted');
      },
      error: (error: unknown) => {
        this.toast.error(
          this.describeError(error, 'The dish could not be deleted.'),
          'Delete failed'
        );
        console.error('Failed to delete dish:', error);
      },
    });
  }

  private toDishType(value: string): DishType {
    return Object.values(DishType).includes(value as DishType)
      ? (value as DishType)
      : DishType.MainCourse;
  }

  private toDishState(value: string): DishState {
    return Object.values(DishState).includes(value as DishState)
      ? (value as DishState)
      : DishState.Available;
  }

  private describeError(error: unknown, fallback: string): string {
    if (error instanceof HttpErrorResponse) {
      const serverMessage = error.error?.message ?? error.error?.error;
      return typeof serverMessage === 'string' && serverMessage.trim()
        ? serverMessage
        : error.message || fallback;
    }
    return error instanceof Error ? error.message : fallback;
  }

  private readImage(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === 'string') resolve(reader.result);
        else reject(new Error('The image could not be converted.'));
      };
      reader.onerror = () => reject(reader.error ?? new Error('The image could not be read.'));
      reader.readAsDataURL(file);
    });
  }
}
