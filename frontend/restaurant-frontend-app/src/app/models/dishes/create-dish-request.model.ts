import { DishState } from '../enums/dish-state.model';
import { DishType } from '../enums/dish-type.model';

export interface CreateDishRequest {
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
  imageBase64?: string;
  state: DishState;
  locationIds: string[];
}
