using APIHandler.Constants.Dishes;
using APIHandler.Entities;
using APIHandler.Exceptions;
using APIHandler.Models.Dishes;
using APIHandler.Repositories.Dishes;
using APIHandler.Repositories.Locations;
using APIHandler.Services.Dishes;
using Moq;

namespace APIHandler.Tests.Services;

public class DishServiceTests
{
    [Fact]
    public async Task UpdateDishAsync_SynchronizesLocationMenuMembership()
    {
        var dish = CreateDish();
        var removedLocation = CreateLocation("location-1", ["dish-1"]);
        var addedLocation = CreateLocation("location-2", []);
        var dishRepository = new Mock<IDishRepository>();
        var locationRepository = new Mock<ILocationRepository>();
        dishRepository.Setup(repository => repository.GetDishByIdAsync("dish-1"))
            .ReturnsAsync(dish);
        locationRepository.Setup(repository => repository.GetAllLocationsAsync())
            .ReturnsAsync(new[] { removedLocation, addedLocation });
        var service = new DishService(dishRepository.Object, locationRepository.Object);

        await service.UpdateDishAsync(
            "dish-1",
            CreateRequest(["location-2"]),
            null);

        Assert.DoesNotContain("dish-1", removedLocation.SpecialtyDishIds!);
        Assert.Contains("dish-1", addedLocation.SpecialtyDishIds!);
        locationRepository.Verify(repository => repository.SaveLocationAsync(removedLocation), Times.Once);
        locationRepository.Verify(repository => repository.SaveLocationAsync(addedLocation), Times.Once);
        dishRepository.Verify(repository => repository.SaveDishAsync(dish), Times.Once);
    }

    [Fact]
    public async Task UpdateDishAsync_RejectsUnknownLocationBeforeSaving()
    {
        var dish = CreateDish();
        var dishRepository = new Mock<IDishRepository>();
        var locationRepository = new Mock<ILocationRepository>();
        dishRepository.Setup(repository => repository.GetDishByIdAsync("dish-1"))
            .ReturnsAsync(dish);
        locationRepository.Setup(repository => repository.GetAllLocationsAsync())
            .ReturnsAsync(Array.Empty<Location>());
        var service = new DishService(dishRepository.Object, locationRepository.Object);

        await Assert.ThrowsAsync<ValidationException>(() =>
            service.UpdateDishAsync("dish-1", CreateRequest(["missing-location"]), null));

        dishRepository.Verify(repository => repository.SaveDishAsync(It.IsAny<Dish>()), Times.Never);
        locationRepository.Verify(repository => repository.SaveLocationAsync(It.IsAny<Location>()), Times.Never);
    }

    private static Dish CreateDish() => new()
    {
        Id = "dish-1",
        Name = "Existing dish",
        Description = "Original description",
        DishType = DishType.MainCourse,
        Price = 10,
        Weight = "300 g",
        Calories = "200",
        Proteins = "10",
        Fats = "5",
        Carbohydrates = "20",
        Vitamins = "C",
        State = DishState.Available,
        LocationId = string.Empty,
    };

    private static Location CreateLocation(string id, List<string> dishIds) => new()
    {
        Id = id,
        Address = $"{id} street",
        Description = "Restaurant location",
        AverageOccupancy = "0",
        SpecialtyDishIds = dishIds,
    };

    private static CreateDishRequest CreateRequest(List<string> locationIds) => new()
    {
        Name = "Updated dish",
        Description = "Updated description",
        DishType = DishType.MainCourse,
        Price = 12,
        Weight = "350 g",
        Calories = "250",
        Proteins = "12",
        Fats = "6",
        Carbohydrates = "24",
        Vitamins = "D",
        State = DishState.Available,
        LocationIds = locationIds,
    };
}
