import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DishModalComponent } from './dish-modal.component';

describe('DishModalComponent', () => {
  let component: DishModalComponent;
  let fixture: ComponentFixture<DishModalComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DishModalComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(DishModalComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('dish', {
      id: 'dish-1',
      name: 'Test dish',
      imageUrl: '',
      price: 10,
      state: 'Available',
      weight: '200g',
      dishType: 'Main',
      description: '',
      calories: '100',
      proteins: '10',
      carbohydrates: '10',
      fats: '5',
      vitamins: '',
    });
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
