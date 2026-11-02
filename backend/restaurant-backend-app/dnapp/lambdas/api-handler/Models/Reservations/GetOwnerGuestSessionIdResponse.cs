using System.Text.Json.Serialization;

namespace APIHandler.Models.Reservations;

public record GetOwnerGuestSessionIdResponse(
    [property: JsonPropertyName("guestSessionId")] string GuestSessionId);
