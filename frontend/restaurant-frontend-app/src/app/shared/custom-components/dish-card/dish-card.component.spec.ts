import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DishCardComponent } from './dish-card.component';
import { DishListResponse } from '@app/models/dishes/dish-list-response.model';
import { DishState } from '@app/models/enums/dish-state.model';

describe('DishCardComponent', () => {
  let component: DishCardComponent;
  let fixture: ComponentFixture<DishCardComponent>;

  const dish: DishListResponse = {
    id: 'dish-1',
    name: 'Khachapuri',
    imageUrl: 'assets/img/dish.png',
    price: 15,
    state: DishState.Available,
    weight: '350',
    dishType: 'MainCourse',
    description: 'Georgian cheese bread',
    calories: '500',
    proteins: '20',
    carbohydrates: '45',
    fats: '25',
    vitamins: 'A, B',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DishCardComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(DishCardComponent);
    component = fixture.componentInstance;

    fixture.componentRef.setInput('dish', dish);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('treats API status labels with spaces as unavailable', () => {
    fixture.componentRef.setInput('dish', { ...dish, state: 'On stop' });
    fixture.detectChanges();

    expect(component.isUnavailable()).toBeTrue();

    fixture.componentRef.setInput('dish', { ...dish, state: 'Out of stock' });
    fixture.detectChanges();

    expect(component.isUnavailable()).toBeTrue();
  });

  it('keeps available dishes orderable', () => {
    fixture.componentRef.setInput('dish', { ...dish, state: 'Available' });
    fixture.detectChanges();

    expect(component.isUnavailable()).toBeFalse();
  });
});
