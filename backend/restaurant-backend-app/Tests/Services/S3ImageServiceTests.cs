using Amazon.Lambda.Core;
using Amazon.S3;
using Amazon.S3.Model;
using APIHandler.Services;
using Moq;

namespace APIHandler.Tests.Services;

public class S3ImageServiceTests
{
    public static IEnumerable<object[]> SupportedImageSignatures =>
    [
        ["image/png", CreatePngHeader()],
        ["image/jpeg", Convert.FromHexString("FFD8FFD9")],
        ["image/webp", Convert.FromHexString("524946460400000057454250")],
        ["image/gif", Convert.FromHexString("47494638396100000000000000")],
        ["image/bmp", Convert.FromHexString("424D000000000000000000000000000000000000000000000000")],
        ["image/tiff", Convert.FromHexString("49492A0008000000")],
    ];

    [Theory]
    [MemberData(nameof(SupportedImageSignatures))]
    public async Task UploadImageAsync_UsesMimeTypeFromImageSignature(
        string expectedContentType,
        byte[] imageBytes)
    {
        PutObjectRequest? capturedRequest = null;
        var s3Client = new Mock<IAmazonS3>();
        s3Client
            .Setup(client => client.PutObjectAsync(
                It.IsAny<PutObjectRequest>(),
                It.IsAny<CancellationToken>()))
            .Callback<PutObjectRequest, CancellationToken>((request, _) => capturedRequest = request)
            .ReturnsAsync(new PutObjectResponse());

        var service = new S3ImageService(s3Client.Object);

        await service.UploadImageAsync(
            imageBytes,
            "test-bucket",
            "test-image",
            Mock.Of<ILambdaLogger>());

        Assert.Equal(expectedContentType, capturedRequest?.ContentType);
    }

    [Fact]
    public async Task UploadImageAsync_RejectsUnknownImageSignature()
    {
        var s3Client = new Mock<IAmazonS3>();
        var service = new S3ImageService(s3Client.Object);

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            service.UploadImageAsync(
                "not-an-image"u8.ToArray(),
                "test-bucket",
                "test-image",
                Mock.Of<ILambdaLogger>()));

        s3Client.Verify(
            client => client.PutObjectAsync(
                It.IsAny<PutObjectRequest>(),
                It.IsAny<CancellationToken>()),
            Times.Never);
    }

    private static byte[] CreatePngHeader()
    {
        var bytes = new byte[33];
        Convert.FromHexString("89504E470D0A1A0A").CopyTo(bytes, 0);
        Convert.FromHexString("0000000D494844520000000100000001").CopyTo(bytes, 8);
        return bytes;
    }
}
