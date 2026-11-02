using APIHandler.Entities;
using APIHandler.Exceptions;
using APIHandler.Models.Dishes;
using APIHandler.Repositories.Dishes;
using APIHandler.Repositories.Locations;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace APIHandler.Services.Dishes;

public class DishService : IDishService
{
    private readonly IDishRepository _dishRepository;
    private readonly ILocationRepository _locationRepository;

    public DishService(IDishRepository dishRepository, ILocationRepository locationRepository)
    {
        _dishRepository = dishRepository ?? throw new ArgumentNullException(nameof(dishRepository));
        _locationRepository = locationRepository ?? throw new ArgumentNullException(nameof(locationRepository));
    }

    public async Task<Dish> GetDishByIdAsync(string dishId)
    {
        var dish = await _dishRepository.GetDishByIdAsync(dishId);
        if (dish is null)
        {
            throw new ValidationException($"Dish with ID {dishId} not found.");
        }

        return dish;
    }

    public async Task<IEnumerable<Dish>> GetDishesByIdsAsync(IEnumerable<string> dishIds)
    {
        return await _dishRepository.GetDishesByIdsAsync(dishIds);
    }

    public async Task<Dish> UpdateDishAsync(string dishId, CreateDishRequest request, string? newImageUrl)
    {
        var existingDish = await _dishRepository.GetDishByIdAsync(dishId)
            ?? throw new ValidationException($"Dish with id '{dishId}' was not found.");
        if (request.LocationIds is null)
            throw new ValidationException("LocationIds must be provided.");

        var locations = (await _locationRepository.GetAllLocationsAsync()).ToList();
        var requestedLocationIds = request.LocationIds.ToHashSet(StringComparer.Ordinal);
        var knownLocationIds = locations.Select(location => location.Id).ToHashSet(StringComparer.Ordinal);
        var unknownLocationIds = requestedLocationIds.Except(knownLocationIds).ToArray();

        if (unknownLocationIds.Length > 0)
        {
            throw new ValidationException(
                $"Location(s) not found: {string.Join(", ", unknownLocationIds)}.");
        }

        existingDish.Name = request.Name;
        existingDish.Description = request.Description;
        existingDish.DishType = request.DishType;
        existingDish.Price = request.Price;
        existingDish.Weight = request.Weight;
        existingDish.Calories = request.Calories;
        existingDish.Proteins = request.Proteins;
        existingDish.Fats = request.Fats;
        existingDish.Carbohydrates = request.Carbohydrates;
        existingDish.Vitamins = request.Vitamins;
        existingDish.State = request.State;

        if (!string.IsNullOrWhiteSpace(newImageUrl))
        {
            existingDish.ImageUrl = newImageUrl;
        }

        await _dishRepository.SaveDishAsync(existingDish);

        foreach (var location in locations)
        {
            var isLinked = location.SpecialtyDishIds?.Contains(dishId) == true;
            var shouldBeLinked = requestedLocationIds.Contains(location.Id);

            if (isLinked == shouldBeLinked)
            {
                continue;
            }

            location.SpecialtyDishIds ??= [];
            if (shouldBeLinked)
                location.SpecialtyDishIds.Add(dishId);
            else
                location.SpecialtyDishIds.Remove(dishId);

            await _locationRepository.SaveLocationAsync(location);
        }

        return existingDish;
    }

    public async Task DeleteDishAsync(string dishId, bool force = false)
    {
        var existingDish = await _dishRepository.GetDishByIdAsync(dishId)
            ?? throw new ValidationException($"Dish with id '{dishId}' was not found.");

        var locations = await _locationRepository.GetAllLocationsAsync();
        var linkedLocations = locations.Where(l => l.SpecialtyDishIds != null && l.SpecialtyDishIds.Contains(dishId)).ToList();

        if (linkedLocations.Count > 0 && !force)
        {
            throw new ValidationException(
                $"Cannot delete dish '{dishId}' because it is currently on the menu of {linkedLocations.Count} location(s)." +
                $" To delete this dish and automatically remove it from all location menus, append '?force=true' to your request URL.");
        }

        if (force)
        {
            foreach (var loc in linkedLocations)
            {
                loc.SpecialtyDishIds!.Remove(dishId);
                await _locationRepository.SaveLocationAsync(loc);
            }
        }

        await _dishRepository.DeleteDishAsync(existingDish);
    }
}